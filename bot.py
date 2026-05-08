import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from gemini_webapi import GeminiClient

Secure_1PSID = "g.a0003QgaN1R9ApbDuNoSqECMZyoMFWOFnd7PY7PqwUmzbNZiA4J2ZZVs3xYkHXFtw24xzUxODgACgYKAcwSARQSFQHGX2Mi5JUov21fKt1j2Qm-WocTHhoVAUF8yKoRTYJV-KSUSKOjG7M2pl9Z0076"
Secure_1PSIDTS = "sidts-CjYBwQ9iI_EXz4AezFx2TIOLmYgPCC41Gz0O5RyXRbvEWivAMgxNT_sKHCXxVttBSk8M1QvrAOoQAA"

FEATURE_IDS = [
    "f3af1c71-b7e9-499a-9012-082968e5ac53",
    "89aa63d8-cfd8-47ce-aa57-b9e45922312b",
    "8fb688a8-fda0-4bb9-b689-376b24093936",
    "743f1005-9c4f-42d8-ba7a-a0bb6fa96e5d",
    "e36a3192-63ad-4cb7-bcf6-8fb113c67991",
    "882eea50-ac42-4e62-ac9c-ce3f050e7a86",
    "ef73c80b-f8be-4392-8aba-9849794fa7e8",
    "ac464f06-6a24-4bdc-a92e-f99db7638f4a",
    "63557177-ab36-415f-8de6-38bcac9ed2b4",
    "a940a567-e965-40d8-b1f2-50d07b0c20fe"
];


BASE_INSTRUCTION = f"""
Bạn là AI sinh dữ liệu xe cho hệ thống Journey Rental.

Yêu cầu:
- Trả về JSON hợp lệ, không có văn bản nào khác ngoài JSON.
- Giữ nguyên định dạng và các trường như ví dụ sau.
- Các trường brandId, modelId để trống "".
- Trường featureIds phải giữ nguyên danh sách sau:
{json.dumps(FEATURE_IDS, indent=4)}
- Trường fuelType phải có dạng "Gasoline" hoặc "Electric" và transmission (AUTOMATIC)(số sàn(tên tiếng anh), (tay côn ( tiếng anh))) (viết hoa toàn bộ).
- Nếu người dùng chỉ nhập tên xe, bạn phải tự sinh mô tả, vị trí, giá thuê, biển số, ảnh phù hợp.
- Nếu là xe máy → type = "MOTORCYCLE".
- Nếu là ô tô → type = "CAR".
- Luôn đảm bảo JSON có dạng:

{{
    "type": "",
    "name": "",
    "brandId": "",
    "modelId": "",
    "licensePlate": "",
    "seats": 0,
    "fuelType": "",
    "transmission": "",
    "pricePerHour": 0,
    "pricePerDay": 0,
    "location": "",
    "city": "",
    "ward": "",
    "latitude": 0,
    "longitude": 0,
    "description": "",
    "terms": [],
    "status": "ACTIVE",
    "images": [],
    "featureIds": []
}}

Chỉ trả về JSON hợp lệ, không thêm bất kỳ lời giải thích nào.
"""


async def generate_vehicle_data(
    client: GeminiClient,
    base_instruction: str,
    vehicle_name: str,
) -> Dict[str, Any]:
    """Send a prompt for a single vehicle and normalize the response."""
    chat = client.start_chat(model="gemini-2.5-flash")
    response_text = ""

    try:
        response = await chat.send_message(f"{base_instruction}\nXe: {vehicle_name}")
        response_text = response.text.strip()

        if response_text.startswith("```"):
            response_text = response_text.strip("`").replace("json", "").strip()

        data = json.loads(response_text)
        data["brandId"] = ""
        data["modelId"] = ""
        data["featureIds"] = FEATURE_IDS

        return {"vehicle": vehicle_name, "success": True, "data": data}

    except json.JSONDecodeError as exc:
        return {
            "vehicle": vehicle_name,
            "success": False,
            "error": f"Không thể parse JSON: {exc}",
            "raw_response": response_text,
        }
    except Exception as exc:  # pylint: disable=broad-except
        error_payload: Dict[str, Any] = {
            "vehicle": vehicle_name,
            "success": False,
            "error": str(exc) or "Unknown error",
        }
        if response_text:
            error_payload["raw_response"] = response_text

        return error_payload


async def _run_batch(
    client: GeminiClient,
    vehicles: List[str],
    concurrency: int,
) -> List[Dict[str, Any]]:
    if concurrency <= 1:
        results = []
        for vehicle in vehicles:
            results.append(await generate_vehicle_data(client, BASE_INSTRUCTION, vehicle))
        return results

    semaphore = asyncio.Semaphore(concurrency)

    async def _safe_generate(vehicle: str) -> Dict[str, Any]:
        async with semaphore:
            return await generate_vehicle_data(client, BASE_INSTRUCTION, vehicle)

    tasks = [asyncio.create_task(_safe_generate(vehicle)) for vehicle in vehicles]
    return await asyncio.gather(*tasks)


async def generate_until_complete(
    vehicles: List[str],
    max_attempts: Optional[int] = None,
    retry_delay: float = 1.0,
    concurrency: int = 1,
) -> List[Dict[str, Any]]:
    client = GeminiClient(Secure_1PSID, Secure_1PSIDTS)
    await client.init(timeout=30, auto_refresh=True)

    attempt_counter = {vehicle: 0 for vehicle in vehicles}
    final_results: Dict[str, Dict[str, Any]] = {vehicle: {} for vehicle in vehicles}
    pending = list(vehicles)
    iteration = 1

    try:
        while pending:
            print(f"👉 Lần chạy {iteration}: {len(pending)} xe đang xử lý...")
            current_batch = list(pending)
            pending = []
            batch_results = await _run_batch(client, current_batch, concurrency)

            for result in batch_results:
                vehicle_name = result["vehicle"]
                attempt_counter[vehicle_name] += 1
                result["attempts"] = attempt_counter[vehicle_name]
                final_results[vehicle_name] = result

                if not result["success"]:
                    attempts_used = attempt_counter[vehicle_name]
                    if max_attempts is None or attempts_used < max_attempts:
                        pending.append(vehicle_name)

            iteration += 1
            if pending and retry_delay > 0:
                await asyncio.sleep(retry_delay)
    finally:
        await client.close()

    return [final_results[vehicle] for vehicle in vehicles]


def prompt_vehicle_list() -> List[str]:
    raw_input_value = input(
        "Nhập danh sách tên xe, phân tách bởi dấu phẩy (vd: 'Xe SH 300i, Xe SH 350i'): "
    ).strip()
    return [item.strip() for item in raw_input_value.split(",") if item.strip()]


def save_results_to_file(
    vehicles: List[str],
    results: List[Dict[str, Any]],
) -> Path:
    output_dir = Path("output/json")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"vehicles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    payload = {
        "generatedAt": datetime.now().isoformat(),
        "vehicles": vehicles,
        "results": results,
    }

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=4)

    return output_path


def load_vehicle_list_from_file(path: Path) -> List[str]:
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {path}")

    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return []

    if path.suffix.lower() == ".json":
        payload = json.loads(content)
        if isinstance(payload, dict):
            candidates = payload.get("vehicles")
            if candidates is None:
                raise ValueError(
                    "JSON phải chứa mảng hoặc khóa 'vehicles' để xác định danh sách xe."
                )
        elif isinstance(payload, list):
            candidates = payload
        else:
            raise ValueError("Định dạng JSON không hợp lệ cho danh sách xe.")

        return [str(item).strip() for item in candidates if str(item).strip()]

    # Mặc định với file .txt: mỗi dòng là một xe
    return [
        line.strip()
        for line in content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sinh dữ liệu xe với Gemini.")
    parser.add_argument(
        "--input-file",
        type=Path,
        help="Đường dẫn tới file chứa danh sách xe (txt/json).",
    )
    parser.add_argument(
        "--vehicles",
        type=str,
        help="Danh sách xe phân tách bởi dấu phẩy (vd: \"Xe SH 300i, Xe SH 350i\").",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=None,
        help="Giới hạn số lần thử mỗi xe (mặc định: không giới hạn).",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=1.0,
        help="Thời gian chờ (giây) giữa các lần chạy lại (mặc định: 1s).",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Số xe xử lý song song trong mỗi lượt (mặc định: 1).",
    )
    return parser.parse_args()


def resolve_vehicle_list(args: argparse.Namespace) -> List[str]:
    if args.input_file:
        vehicles = load_vehicle_list_from_file(args.input_file)
        print(f"Đã đọc {len(vehicles)} xe từ file {args.input_file}.")
        return vehicles

    if args.vehicles:
        vehicles = [item.strip() for item in args.vehicles.split(",") if item.strip()]
        if vehicles:
            print(f"Sử dụng {len(vehicles)} xe từ tham số --vehicles.")
        return vehicles

    return prompt_vehicle_list()


async def main():
    args = parse_arguments()

    try:
        vehicles = resolve_vehicle_list(args)
    except Exception as exc:  # pylint: disable=broad-except
        print(f"Không thể tải danh sách xe: {exc}")
        return

    if not vehicles:
        print("Không có xe nào được cung cấp.")
        return

    print(f"Đang sinh dữ liệu cho {len(vehicles)} xe...")
    results = await generate_until_complete(
        vehicles,
        max_attempts=args.max_attempts,
        retry_delay=args.retry_delay,
        concurrency=max(1, args.concurrency or 1),
    )

    for result in results:
        status = "✅" if result["success"] else "⚠️"
        print(f"{status} {result['vehicle']}")

    output_path = save_results_to_file(vehicles, results)
    print(f"Dữ liệu đã được lưu tại: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
