"""
AI Client module for calling Gemini via gemini_webapi
"""
import asyncio
import atexit
import concurrent.futures
import base64
import json
import os
import shutil
import subprocess
import tempfile
import threading
from io import BytesIO
from typing import Optional
from PIL import Image
import re
from gemini_webapi import GeminiClient

from config import (
    PROMPT_TEMPLATE, 
    get_gemini_cookies,
    GEMINI_MODEL,
    IMAGE_MAX_WIDTH,
    IMAGE_MAX_HEIGHT,
    IMAGE_QUALITY,
    USE_PNG,
    USE_GEMINI_CLI,
    GEMINI_CLI_COMMAND,
    GEMINI_CLI_TIMEOUT,
    GEMINI_CLI_FALLBACK_TO_WEBAPI,
    GEMINI_CLI_APPROVAL_MODE,
    GEMINI_CLI_MODEL,
    GEMINI_WEBAPI_TIMEOUT,
)


_WORKER_LOOP = None
_WORKER_THREAD = None
_WORKER_READY = threading.Event()
_PERSISTENT_CLIENT = None
_PERSISTENT_CLIENT_COOKIE_KEY = None


def _ensure_worker_loop_started() -> None:
    """Start a dedicated asyncio loop thread for persistent Gemini operations."""
    global _WORKER_LOOP, _WORKER_THREAD
    if _WORKER_THREAD and _WORKER_THREAD.is_alive():
        return

    _WORKER_READY.clear()

    def _runner() -> None:
        global _WORKER_LOOP
        _WORKER_LOOP = asyncio.new_event_loop()
        asyncio.set_event_loop(_WORKER_LOOP)
        _WORKER_READY.set()
        _WORKER_LOOP.run_forever()

    _WORKER_THREAD = threading.Thread(target=_runner, name="gemini-worker-loop", daemon=True)
    _WORKER_THREAD.start()
    _WORKER_READY.wait(timeout=3)


def _run_on_worker_loop(coro, timeout: Optional[float] = None):
    """Run a coroutine on the dedicated worker loop and wait for its result."""
    _ensure_worker_loop_started()
    future = asyncio.run_coroutine_threadsafe(coro, _WORKER_LOOP)
    try:
        return future.result(timeout=timeout)
    except concurrent.futures.TimeoutError as exc:
        future.cancel()
        raise TimeoutError(f"Worker loop task timed out after {timeout} seconds") from exc


def _cookie_key(cookies: dict) -> tuple:
    return (cookies.get("Secure_1PSID", ""), cookies.get("Secure_1PSIDTS", ""))


async def _get_or_init_client(cookies: dict) -> GeminiClient:
    """Create once and reuse Gemini client across screenshot requests."""
    global _PERSISTENT_CLIENT, _PERSISTENT_CLIENT_COOKIE_KEY

    current_key = _cookie_key(cookies)
    if _PERSISTENT_CLIENT and _PERSISTENT_CLIENT_COOKIE_KEY == current_key:
        return _PERSISTENT_CLIENT

    if _PERSISTENT_CLIENT:
        try:
            await _PERSISTENT_CLIENT.close()
        except Exception:
            pass

    client = GeminiClient(cookies["Secure_1PSID"], cookies["Secure_1PSIDTS"])
    await client.init(timeout=30, auto_refresh=True)
    _PERSISTENT_CLIENT = client
    _PERSISTENT_CLIENT_COOKIE_KEY = current_key
    print("[DEBUG] Gemini client initialized (persistent)")
    return _PERSISTENT_CLIENT


async def _reset_persistent_client() -> None:
    """Drop current client so next request can re-initialize cleanly."""
    global _PERSISTENT_CLIENT, _PERSISTENT_CLIENT_COOKIE_KEY
    if _PERSISTENT_CLIENT:
        try:
            await _PERSISTENT_CLIENT.close()
        except Exception:
            pass
    _PERSISTENT_CLIENT = None
    _PERSISTENT_CLIENT_COOKIE_KEY = None


def _shutdown_worker() -> None:
    """Gracefully close persistent client and stop background loop on process exit."""
    global _WORKER_LOOP, _WORKER_THREAD
    try:
        if _WORKER_LOOP and _WORKER_LOOP.is_running():
            _run_on_worker_loop(_reset_persistent_client())
            _WORKER_LOOP.call_soon_threadsafe(_WORKER_LOOP.stop)
    except Exception:
        pass
    finally:
        _WORKER_LOOP = None
        _WORKER_THREAD = None


atexit.register(_shutdown_worker)


def optimize_image(image: Image.Image) -> Image.Image:
    """
    Optimize image by resizing if needed (or keep original for best quality)
    
    Args:
        image: PIL Image object
    
    Returns:
        Optimized PIL Image object (or original if no resize needed)
    """
    original_width, original_height = image.size
    print(f"[DEBUG] Original image size: {original_width}x{original_height}")
    
    # If max dimensions are very high (99999), don't resize - keep original quality
    if IMAGE_MAX_WIDTH >= 99999 or IMAGE_MAX_HEIGHT >= 99999:
        print(f"[DEBUG] High quality mode: No resize, keeping original size")
        return image
    
    # Calculate new size maintaining aspect ratio
    if original_width <= IMAGE_MAX_WIDTH and original_height <= IMAGE_MAX_HEIGHT:
        print(f"[DEBUG] Image already within limits, no resize needed")
        return image
    
    # Calculate scaling factor
    width_ratio = IMAGE_MAX_WIDTH / original_width
    height_ratio = IMAGE_MAX_HEIGHT / original_height
    ratio = min(width_ratio, height_ratio)
    
    new_width = int(original_width * ratio)
    new_height = int(original_height * ratio)
    
    # Resize image using high-quality resampling
    optimized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    print(f"[DEBUG] Optimized image size: {new_width}x{new_height} (ratio: {ratio:.2f})")
    
    return optimized_image


def image_to_data_uri(image: Image.Image) -> str:
    """
    Convert PIL Image to data URI format (base64)
    Uses PNG for best quality (lossless) or JPEG for compression
    
    Args:
        image: PIL Image object
    
    Returns:
        Data URI string: data:image/png;base64,... or data:image/jpeg;base64,...
    """
    # Optimize image first (may resize or keep original)
    optimized_image = optimize_image(image)
    
    buffered = BytesIO()
    
    if USE_PNG:
        # Use PNG format for lossless quality (best quality, no compression)
        optimized_image.save(buffered, format="PNG", optimize=True)
        mime_type = "image/png"
        format_name = "PNG (lossless)"
    else:
        # Use JPEG format for compression (smaller file size)
        optimized_image.save(
            buffered, 
            format="JPEG", 
            quality=IMAGE_QUALITY,
            optimize=True
        )
        mime_type = "image/jpeg"
        format_name = f"JPEG (quality={IMAGE_QUALITY})"
    
    image_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    file_size_kb = len(image_base64) / 1024
    file_size_mb = file_size_kb / 1024
    print(f"[DEBUG] Image format: {format_name}")
    print(f"[DEBUG] Image data size: {file_size_kb:.2f} KB ({file_size_mb:.2f} MB base64)")
    
    return f"data:{mime_type};base64,{image_base64}"


def extract_answer(response_text: str) -> Optional[str]:
    """
    Extract answer(s) from AI response
    Supports single answer (A) or multiple answers (AB, A,B, A B)
    
    Args:
        response_text: Raw response text from AI
    
    Returns:
        Answer string (e.g., "A", "AB", "A,B", "ABC") or None if not found
    """
    # Handle None or empty response
    if not response_text:
        return None

    # Prefer structured parsing first to avoid false positives like defaulting to 'A'.
    structured = _extract_structured_answer(response_text)
    if structured:
        print(f"[DEBUG] Structured answer extracted: {structured}")
        return structured
    
    print(f"[DEBUG] Raw response text: {repr(response_text)}")
    
    # Clean the response text
    response_text_clean = response_text.strip().upper()

    # Strategy 1: Accept only a strict token response (A / AB / A,B / A B)
    token = _normalize_answer_value(response_text_clean)
    if token:
        print(f"[DEBUG] Found strict token answer: {token}")
        return token

    # Strategy 2: Look for "Đáp án: A" or "Answer: AB" pattern with multiple answers
    answer_pattern = r'(?:\bđáp\s*án\b|\banswer\b|\bkết\s*quả\b|\bkết\s*luận\b)[\s:]*([ABCD\s,]+)'
    answer_match = re.search(answer_pattern, response_text_clean, re.IGNORECASE)
    if answer_match:
        answer_str = answer_match.group(1).upper()
        token = _normalize_answer_value(answer_str)
        if token:
            print(f"[DEBUG] Found answer in pattern: {token}")
            return token

    print(f"[DEBUG] Could not extract answer from: {response_text}")
    return None


def _normalize_answer_value(value: str) -> Optional[str]:
    """Normalize answer strings like 'A,B'/'A B'/'AB' to canonical form 'AB'."""
    if not isinstance(value, str):
        return None
    upper = value.upper().strip()
    # Strict format only: A/B/C/D separated by optional spaces or commas.
    if not re.fullmatch(r"[ABCD](?:[\s,]*[ABCD]){0,3}", upper):
        return None

    cleaned = re.sub(r"[^ABCD]", "", upper)
    if not cleaned:
        return None

    # Preserve original order while removing duplicates.
    deduped = ""
    for ch in cleaned:
        if ch not in deduped:
            deduped += ch

    if re.fullmatch(r"[ABCD]{1,4}", deduped):
        return deduped
    return None


def _extract_structured_answer(text: str) -> Optional[str]:
    """Extract answer from strict structures (JSON/object/standalone token) only."""
    if not text:
        return None

    stripped = text.strip()
    if not stripped:
        return None

    # Case 1: plain token output (ideal): A / AB / A,B / A B
    token = _normalize_answer_value(stripped)
    if token:
        return token

    # Case 2: fenced JSON block
    fence_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", stripped, re.IGNORECASE)
    if fence_match:
        try:
            payload = json.loads(fence_match.group(1))
            if isinstance(payload, dict):
                token = _normalize_answer_value(str(payload.get("answer", "")))
                if token:
                    return token
        except Exception:
            pass

    # Case 3: any JSON object containing an 'answer' field
    for obj_match in re.finditer(r"\{[\s\S]*?\}", stripped):
        obj_text = obj_match.group(0)
        try:
            payload = json.loads(obj_text)
            if isinstance(payload, dict):
                token = _normalize_answer_value(str(payload.get("answer", "")))
                if token:
                    return token
        except Exception:
            continue

    # Case 4: quoted answer key in non-JSON text
    key_match = re.search(r'"answer"\s*:\s*"([ABCD\s,]+)"', stripped, re.IGNORECASE)
    if key_match:
        token = _normalize_answer_value(key_match.group(1))
        if token:
            return token

    return None


def _is_transient_gemini_error(exc: Exception) -> bool:
    """Return True for temporary upstream failures that are worth retrying."""
    msg = str(exc).lower()
    transient_markers = [
        "silently aborted",
        "queueing",
        "socket idle",
        "timeout",
        "temporar",
        "connection",
        "429",
        "503",
    ]
    return any(marker in msg for marker in transient_markers)


def _extract_text_from_cli_output(raw_output: str) -> str:
    """Extract a useful text payload from Gemini CLI output."""
    if not raw_output:
        return ""

    stripped = raw_output.strip()
    if not stripped:
        return ""

    json_answer = _try_extract_cli_answer(raw_output)
    if json_answer:
        return json_answer

    try:
        payload = json.loads(stripped)

        # Common direct keys first.
        for key in ("text", "response", "output", "content"):
            value = payload.get(key) if isinstance(payload, dict) else None
            if isinstance(value, str) and value.strip():
                return value.strip()

        # Generic recursive fallback for unknown output schemas.
        def _walk(obj):
            if isinstance(obj, str) and obj.strip():
                return obj.strip()
            if isinstance(obj, dict):
                for v in obj.values():
                    found = _walk(v)
                    if found:
                        return found
            if isinstance(obj, list):
                for v in obj:
                    found = _walk(v)
                    if found:
                        return found
            return None

        found_text = _walk(payload)
        if found_text:
            return found_text
    except Exception:
        pass

    return stripped


def _try_extract_cli_answer(raw_output: str) -> Optional[str]:
    """Return answer text only when a complete JSON payload is present."""
    if not raw_output:
        return None

    stripped = raw_output.strip()
    if not stripped:
        return None

    payload = None
    try:
        payload = json.loads(stripped)
    except Exception:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            payload = json.loads(stripped[start:end + 1])
        except Exception:
            return None

    if not isinstance(payload, dict):
        return None

    # Prefer explicit answer field first.
    direct_answer = payload.get("answer")
    if isinstance(direct_answer, str) and direct_answer.strip():
        return direct_answer.strip()

    for key in ("text", "response", "output", "content"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return None


def _run_gemini_cli_via_cmd_redirection(
    cmd: list[str],
    timeout_seconds: int,
    stdin_text: Optional[str] = None,
) -> tuple[int, str, str]:
    """Run Gemini CLI through cmd.exe and capture output via files (stable on Windows)."""
    out_file = tempfile.NamedTemporaryFile(delete=False, suffix=".gemini.out.txt")
    err_file = tempfile.NamedTemporaryFile(delete=False, suffix=".gemini.err.txt")
    out_path = out_file.name
    err_path = err_file.name
    out_file.close()
    err_file.close()
    in_path = None

    try:
        if stdin_text is not None:
            in_file = tempfile.NamedTemporaryFile(delete=False, suffix=".gemini.in.txt", mode="w", encoding="utf-8")
            in_file.write(stdin_text)
            in_file.flush()
            in_path = in_file.name
            in_file.close()

        command_str = subprocess.list2cmdline(cmd)
        if in_path:
            shell_cmd = f'cmd.exe /d /s /c "{command_str} <\"{in_path}\" 1>\"{out_path}\" 2>\"{err_path}\""'
        else:
            shell_cmd = f'cmd.exe /d /s /c "{command_str} 1>\"{out_path}\" 2>\"{err_path}\""'

        startupinfo = None
        creationflags = 0
        if os.name == "nt":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE
            creationflags = subprocess.CREATE_NO_WINDOW

        try:
            completed = subprocess.run(
                shell_cmd,
                check=False,
                timeout=timeout_seconds,
                startupinfo=startupinfo,
                creationflags=creationflags,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(
                f"Gemini CLI timed out after {timeout_seconds}s. "
                "CLI process did not finish in time."
            ) from exc

        with open(out_path, "r", encoding="utf-8", errors="replace") as f:
            stdout = f.read()
        with open(err_path, "r", encoding="utf-8", errors="replace") as f:
            stderr = f.read()

        return completed.returncode or 0, stdout, stderr
    finally:
        for p in (out_path, err_path, in_path):
            if not p:
                continue
            try:
                os.unlink(p)
            except Exception:
                pass


def _analyze_question_with_gemini_cli(image: Image.Image) -> Optional[str]:
    """Analyze screenshot via Gemini CLI using Tesseract OCR to extract text first."""
    import pytesseract
    import platform
    import os

    # Automatically set Tesseract path for Windows if it exists in the default location
    if platform.system() == "Windows":
        default_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if os.path.exists(default_path):
            pytesseract.pytesseract.tesseract_cmd = default_path

    optimized_image = optimize_image(image)
    print(f"[DEBUG] Image size: {optimized_image.size[0]}x{optimized_image.size[1]} pixels")
    try:
        print("[DEBUG] Extracting text using Tesseract OCR...")
        try:
            try:
                # Try using Vietnamese if available
                extracted_text = pytesseract.image_to_string(optimized_image, lang='vie')
            except Exception:
                # Fallback to default (usually English)
                extracted_text = pytesseract.image_to_string(optimized_image)
        except pytesseract.TesseractNotFoundError:
            print("\n[ERROR] Tesseract OCR không được tìm thấy trên máy của bạn!")
            print("Vui lòng tải và cài đặt Tesseract từ: https://github.com/UB-Mannheim/tesseract/wiki")
            print("Lưu ý: Nhớ tick chọn gói ngôn ngữ 'Vietnamese' trong phần 'Additional language data (download)' lúc cài đặt.")
            print("Nếu rành, bạn có thể chỉnh lại đường dẫn trong ai_client.py.")
            return None

        print(f"[DEBUG] OCR Extracted Text: {extracted_text[:200]}...")

        # Keep -p short to avoid Windows/cmd quoting issues on long multiline prompts.
        cli_prompt = "Read prompt from stdin and reply with JSON only."

        stdin_payload = (
            "Ban la bo may tra loi trac nghiem.\n"
            "Duoi day la van ban duoc trich xuat tu anh cua mot cau hoi trac nghiem:\n"
            "========================\n"
            f"{extracted_text}\n"
            "========================\n"
            f"{PROMPT_TEMPLATE}\n\n"
            "Tra ve CHINH XAC mot JSON object co dang:\n"
            '{"answer":"A"} hoac {"answer":"AB"}.\n'
            "Khong tra ve text nao khac ngoai JSON object tren.\n"
        )

        cmd = [
            GEMINI_CLI_COMMAND,
            "-p",
            cli_prompt,
            "-m",
            GEMINI_CLI_MODEL,
            "--output-format",
            "json",
            "--approval-mode",
            GEMINI_CLI_APPROVAL_MODE,
        ]

        executable = shutil.which(GEMINI_CLI_COMMAND)
        if not executable:
            raise FileNotFoundError(
                f"Gemini CLI command not found: {GEMINI_CLI_COMMAND}. "
                "Install with: npm install -g @google/gemini-cli"
            )

        print(f"[DEBUG] Sending to Gemini CLI: {GEMINI_CLI_COMMAND}")
        return_code, stdout_raw, stderr_raw = _run_gemini_cli_via_cmd_redirection(
            cmd,
            GEMINI_CLI_TIMEOUT,
            stdin_text=stdin_payload,
        )

        stdout = (stdout_raw or "").strip()
        stderr = (stderr_raw or "").strip()
        if stderr:
            print(f"[DEBUG] Gemini CLI stderr (head): {stderr[:300]}")

        if return_code != 0:
            raise RuntimeError(
                f"Gemini CLI failed (code={return_code}): {stderr or stdout or 'Unknown error'}"
            )

        answer_text = _extract_text_from_cli_output(stdout)
        if not answer_text:
            # Some Gemini CLI builds emit useful text on stderr.
            answer_text = _extract_text_from_cli_output(stderr)
        if not answer_text:
            answer_text = _extract_text_from_cli_output(f"{stdout}\n{stderr}")
        print(f"[DEBUG] AI response content (raw): {repr(answer_text)}")
        print(f"[DEBUG] AI response content (display): {answer_text}")

        if not answer_text:
            print("[ERROR] Gemini CLI returned empty content")
            return None

        print(f"[DEBUG] Extracting answer from: {answer_text}")
        answer = _extract_structured_answer(answer_text) or extract_answer(answer_text)
        print(f"[DEBUG] Final extracted answer: {answer}")
        return answer
    except Exception as e:
        print(f"Error calling Gemini CLI: {e}")
        raise


async def _analyze_question_async(image: Image.Image, cookies: dict) -> Optional[str]:
    """
    Async helper to analyze question using gemini_webapi
    """
    client = None
    temp_image_path = None
    
    try:
        # Reuse one persistent client across multiple screenshot requests.
        client = await _get_or_init_client(cookies)
        
        # Optimize image
        optimized_image = optimize_image(image)
        print(f"[DEBUG] Image size: {optimized_image.size[0]}x{optimized_image.size[1]} pixels")
        
        # Save image to temp file (gemini_webapi requires file path)
        import tempfile
        suffix = '.png' if USE_PNG else '.jpg'
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_image_path = temp_file.name
        temp_file.close()

        if USE_PNG:
            optimized_image.save(temp_image_path, format='PNG', optimize=True)
        else:
            # JPEG is typically much smaller for screenshots and faster to upload.
            optimized_image.convert('RGB').save(
                temp_image_path,
                format='JPEG',
                quality=IMAGE_QUALITY,
                optimize=True
            )

        import os
        file_size_kb = os.path.getsize(temp_image_path) / 1024
        print(f"[DEBUG] Saved temp image to: {temp_image_path}")
        print(f"[DEBUG] Temp image size: {file_size_kb:.2f} KB")
        
        # Use configured model when provided, otherwise account default model.
        # Keep fallback responsive: fail fast instead of waiting too long.
        send_timeout_seconds = min(20, max(5, GEMINI_WEBAPI_TIMEOUT - 5))
        max_retries = 1
        response = None

        for attempt in range(1, max_retries + 1):
            chat = client.start_chat(model=GEMINI_MODEL) if GEMINI_MODEL else client.start_chat()
            if GEMINI_MODEL:
                print(f"[DEBUG] Sending to Gemini (model={GEMINI_MODEL}) attempt {attempt}/{max_retries}")
            else:
                print(f"[DEBUG] Sending to Gemini (using account's default model) attempt {attempt}/{max_retries}")

            try:
                # Fail fast on long queueing, then retry once.
                response = await asyncio.wait_for(
                    chat.send_message(PROMPT_TEMPLATE, files=[temp_image_path]),
                    timeout=send_timeout_seconds,
                )
                break
            except asyncio.TimeoutError as e:
                print(f"[WARN] Gemini request timeout after {send_timeout_seconds}s (attempt {attempt}/{max_retries})")
                if attempt >= max_retries:
                    raise e
                await _reset_persistent_client()
                client = await _get_or_init_client(cookies)
            except Exception as e:
                if _is_transient_gemini_error(e) and attempt < max_retries:
                    print(f"[WARN] Transient Gemini error, retrying: {e}")
                    await _reset_persistent_client()
                    client = await _get_or_init_client(cookies)
                    continue
                raise

        if response is None:
            raise RuntimeError("No response returned from Gemini after retries")
        
        print(f"[DEBUG] Response received from Gemini")
        
        # Extract text from response
        answer_text = response.text.strip()
        
        print(f"[DEBUG] AI response content (raw): {repr(answer_text)}")
        print(f"[DEBUG] AI response content (display): {answer_text}")
        
        if not answer_text:
            print("[ERROR] Model returned empty content")
            return None
        
        # Extract answer letter
        print(f"[DEBUG] Extracting answer from: {answer_text}")
        answer = _extract_structured_answer(answer_text) or extract_answer(answer_text)
        print(f"[DEBUG] Final extracted answer: {answer}")
        
        return answer
        
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Clean up temp file
        if temp_image_path:
            try:
                import os
                os.unlink(temp_image_path)
                print(f"[DEBUG] Cleaned up temp image: {temp_image_path}")
            except:
                pass


def analyze_question(image: Image.Image) -> Optional[str]:
    """
    Analyze a screenshot containing a multiple choice question and return the answer(s)
    Uses gemini_webapi with cookies (like bot.py)
    Supports single answer (A) or multiple answers (AB, ABC, etc.)
    
    Args:
        image: PIL Image object containing the question
    
    Returns:
        Answer string (e.g., "A", "AB", "ABC") or None if error
    """
    try:
        if USE_GEMINI_CLI:
            try:
                cli_answer = _analyze_question_with_gemini_cli(image)
                if cli_answer:
                    return cli_answer
                print("[WARN] Gemini CLI returned empty answer.")
                if not GEMINI_CLI_FALLBACK_TO_WEBAPI:
                    return None
            except Exception as cli_error:
                print(f"[WARN] Gemini CLI path failed: {cli_error}")
                if not GEMINI_CLI_FALLBACK_TO_WEBAPI:
                    return None

        cookies = get_gemini_cookies()
        if not cookies:
            raise ValueError(
                "Gemini cookies not found. Please set them in config.py or .env file, "
                "or configure Gemini CLI authentication."
            )

        # Fallback path: run on background worker loop with a hard timeout.
        return _run_on_worker_loop(
            _analyze_question_async(image, cookies),
            timeout=GEMINI_WEBAPI_TIMEOUT,
        )
    except TimeoutError as e:
        print(f"[ERROR] Request timeout: {e}")
        try:
            # Best effort reset to avoid stale/hung connection state for next request.
            _run_on_worker_loop(_reset_persistent_client(), timeout=5)
        except Exception:
            pass
        return None
    except Exception as e:
        print(f"Error in analyze_question: {e}")
        import traceback
        traceback.print_exc()
        return None
