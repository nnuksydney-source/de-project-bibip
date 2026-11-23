import os
import json
from decimal import Decimal
from datetime import datetime
from typing import Optional
from models import Car, CarFullInfo, CarStatus, Model, ModelSaleStats, Sale


class CarService:
    LINE_LENGTH = 500
    FULL_LINE_LENGTH = 501

    def __init__(self, root_directory_path: str) -> None:
        self.root_dir = root_directory_path
        os.makedirs(self.root_dir, exist_ok=True)
        self.cars_file = os.path.join(self.root_dir, "cars.txt")
        self.cars_index_file = os.path.join(self.root_dir, "cars_index.txt")
        self.models_file = os.path.join(self.root_dir, "models.txt")
        self.models_index_file = os.path.join(self.root_dir, "models_index.txt")
        self.sales_file = os.path.join(self.root_dir, "sales.txt")
        self.sales_index_file = os.path.join(self.root_dir, "sales_index.txt")

    def _read_index(self, index_path: str) -> list[tuple[str, int]]:
        index_data: list[tuple[str, int]] = []
        if not os.path.exists(index_path):
            return index_data
        with open(index_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    key, row_num = line.split(";")
                    index_data.append((key, int(row_num)))
        return index_data

    def _write_index(self, index_path: str, index_data: list[tuple[str, int]]) -> None:
        index_data.sort(key=lambda x: x[0])
        with open(index_path, "w", encoding="utf-8") as f:
            for key, row_num in index_data:
                f.write(f"{key};{row_num}\n")

    def _find_row_in_index(self, index_data: list[tuple[str, int]], target_key: str) -> Optional[int]:
        left, right = 0, len(index_data) - 1
        while left <= right:
            mid = (left + right) // 2
            if index_data[mid][0] == target_key:
                return index_data[mid][1]
            elif index_data[mid][0] < target_key:
                left = mid + 1
            else:
                right = mid - 1
        return None

    def _write_line(self, file_path: str, row_num: int, data_dict: dict) -> None:
        raw_str = json.dumps(data_dict, ensure_ascii=False, default=str)
        if len(raw_str) > self.LINE_LENGTH:
            raise ValueError(f"Строка превышает лимит в {self.LINE_LENGTH} символов")
        padded_str = raw_str.ljust(self.LINE_LENGTH) + "\n"
        mode = "r+b" if os.path.exists(file_path) and os.path.getsize(file_path) > 0 else "wb"
        with open(file_path, mode) as f:
            f.seek(row_num * self.FULL_LINE_LENGTH)
            f.write(padded_str.encode("utf-8"))

    def _read_line(self, file_path: str, row_num: int) -> Optional[dict]:
        with open(file_path, "rb") as f:
            f.seek(row_num * self.FULL_LINE_LENGTH)
            raw_bytes = f.read(self.LINE_LENGTH)
            if not raw_bytes:
                return None
            content = raw_bytes.decode("utf-8").strip()
            if not content:
                return None
            return json.loads(content)

    def _get_total_rows(self, file_path: str) -> int:
        if not os.path.exists(file_path):
            return 0
        return os.path.getsize(file_path) // self.FULL_LINE_LENGTH

    def add_model(self, model: Model) -> Model:
        index_data = self._read_index(self.models_index_file)
        row_num = self._get_total_rows(self.models_file)

        data = {
            "id": model.id,
            "name": model.name,
            "brand": model.brand,
        }
        self._write_line(self.models_file, row_num, data)

        index_data.append((str(model.id), row_num))
        self._write_index(self.models_index_file, index_data)
        return model

    def add_car(self, car: Car) -> Car:
        index_data = self._read_index(self.cars_index_file)
        row_num = self._get_total_rows(self.cars_file)

        data = {
            "vin": car.vin,
            "model": car.model,
            "price": str(car.price),
            "date_start": car.date_start.isoformat(),
            "status": car.status.value if hasattr(car.status, "value") else str(car.status),
        }
        self._write_line(self.cars_file, row_num, data)

        index_data.append((car.vin, row_num))
        self._write_index(self.cars_index_file, index_data)
        return car

    def sell_car(self, sale: Sale) -> Car:
        sales_index = self._read_index(self.sales_index_file)
        sale_row_num = self._get_total_rows(self.sales_file)

        sale_data = {
            "sales_number": sale.sales_number,
            "car_vin": sale.car_vin,
            "sales_date": sale.sales_date.isoformat(),
            "cost": str(sale.cost),
            "is_deleted": False,
        }
        self._write_line(self.sales_file, sale_row_num, sale_data)
        sales_index.append((sale.sales_number, sale_row_num))
        self._write_index(self.sales_index_file, sales_index)
        cars_index = self._read_index(self.cars_index_file)
        car_row_num = self._find_row_in_index(cars_index, sale.car_vin)
        if car_row_num is None:
            raise ValueError(f"Автомобиль с VIN {sale.car_vin} не найден")
        car_dict = self._read_line(self.cars_file, car_row_num)
        car_dict["status"] = CarStatus.sold.value
        self._write_line(self.cars_file, car_row_num, car_dict)

        return Car(
            vin=car_dict["vin"],
            model=int(car_dict["model"]),
            price=Decimal(car_dict["price"]),
            date_start=datetime.fromisoformat(car_dict["date_start"]), 
            status=CarStatus(car_dict["status"]),
        )

    def get_cars(self, status: CarStatus) -> list[Car]:
        available_cars = []
        total_rows = self._get_total_rows(self.cars_file)
        target_status = status.value if hasattr(status, "value") else str(status)

        for row_num in range(total_rows):
            car_dict = self._read_line(self.cars_file, row_num)
            if car_dict and car_dict.get("status") == target_status:
                available_cars.append(
                    Car( 
                        vin=car_dict["vin"],
                        model=int(car_dict["model"]),
                        price=Decimal(car_dict["price"]),
                        date_start=datetime.fromisoformat(car_dict["date_start"]),
                        status=CarStatus(car_dict["status"]),
                    )
                )

        return available_cars

    def get_car_info(self, vin: str) -> Optional[CarFullInfo]:
        cars_index = self._read_index(self.cars_index_file)
        car_row_num = self._find_row_in_index(cars_index, vin)
        if car_row_num is None:
            return None  
        car_dict = self._read_line(self.cars_file, car_row_num)
        if not car_dict:
            return None
        models_index = self._read_index(self.models_index_file)
        model_row_num = self._find_row_in_index(models_index, str(car_dict["model"]))
        model_dict = self._read_line(self.models_file, model_row_num) if model_row_num is not None else {}
        sales_date = None
        sales_cost = None
        if car_dict["status"] == CarStatus.sold.value:
            total_sales = self._get_total_rows(self.sales_file)
            for row_num in range(total_sales):
                sale_dict = self._read_line(self.sales_file, row_num)
                if (
                    sale_dict
                    and not sale_dict.get("is_deleted", False)  
                    and sale_dict.get("car_vin") == vin
                ):
                    sales_date = datetime.fromisoformat(sale_dict["sales_date"])
                    sales_cost = Decimal(sale_dict["cost"])
                    break

        return CarFullInfo(
            vin=car_dict["vin"],
            car_model_name=model_dict.get("name", ""),
            car_model_brand=model_dict.get("brand", ""),
            price=Decimal(car_dict["price"]),
            date_start=datetime.fromisoformat(car_dict["date_start"]),
            status=CarStatus(car_dict["status"]),
            sales_date=sales_date,
            sales_cost=sales_cost,
        )

    def update_vin(self, vin: str, new_vin: str) -> Car:
        cars_index = self._read_index(self.cars_index_file)
        car_row_num = self._find_row_in_index(cars_index, vin)
        if car_row_num is None:  
            raise ValueError(f"Автомобиль с VIN {vin} не найден")

        car_dict = self._read_line(self.cars_file, car_row_num)
        car_dict["vin"] = new_vin
        self._write_line(self.cars_file, car_row_num, car_dict)

        updated_index = [
            (new_vin, r_num) if k == vin else (k, r_num)
            for k, r_num in cars_index
        ]
        self._write_index(self.cars_index_file, updated_index)

        return Car(
            vin=car_dict["vin"],
            model=int(car_dict["model"]),
            price=Decimal(car_dict["price"]), 
            date_start=datetime.fromisoformat(car_dict["date_start"]),
            status=CarStatus(car_dict["status"]),
        )

    def revert_sale(self, sales_number: str) -> Car:
        sales_index = self._read_index(self.sales_index_file)
        sale_row_num = self._find_row_in_index(sales_index, sales_number)
        if sale_row_num is None:
            raise ValueError(f"Продажа {sales_number} не найдена")
        sale_dict = self._read_line(self.sales_file, sale_row_num)
        sale_dict["is_deleted"] = True
        self._write_line(self.sales_file, sale_row_num, sale_dict)
        updated_sales_index = [(k, r) for k, r in sales_index if k != sales_number]
        self._write_index(self.sales_index_file, updated_sales_index)
        car_vin = sale_dict["car_vin"]
        cars_index = self._read_index(self.cars_index_file)
        car_row_num = self._find_row_in_index(cars_index, car_vin)
        car_dict = self._read_line(self.cars_file, car_row_num)
        car_dict["status"] = CarStatus.available.value
        self._write_line(self.cars_file, car_row_num, car_dict)
        return Car(  
            vin=car_dict["vin"],
            model=int(car_dict["model"]),
            price=Decimal(car_dict["price"]),
            date_start=datetime.fromisoformat(car_dict["date_start"]),
            status=CarStatus(car_dict["status"]),
        )

    def top_models_by_sales(self) -> list[ModelSaleStats]:
        cars_index = self._read_index(self.cars_index_file)
        models_index = self._read_index(self.models_index_file)
        sales_stats: dict[int, dict] = {}
        total_sales = self._get_total_rows(self.sales_file)
        for row_num in range(total_sales):
            sale_dict = self._read_line(self.sales_file, row_num)
            if not sale_dict or sale_dict.get("is_deleted", False):
                continue
            car_vin = sale_dict["car_vin"]
            car_row = self._find_row_in_index(cars_index, car_vin)
            if car_row is None:
                continue
            car_dict = self._read_line(self.cars_file, car_row)
            model_id = int(car_dict["model"])
            car_price = Decimal(car_dict["price"])
            if model_id not in sales_stats:
                sales_stats[model_id] = {"count": 0, "total_price": Decimal("0")}
            sales_stats[model_id]["count"] += 1
            sales_stats[model_id]["total_price"] += car_price
        sorted_models = sorted(
            sales_stats.items(),
            key=lambda item: (item[1]["count"], item[1]["total_price"] / item[1]["count"]),
            reverse=True,
        )[:3]
        result = []
        for model_id, stats in sorted_models:
            model_row = self._find_row_in_index(models_index, str(model_id))
            if model_row is not None:
                model_dict = self._read_line(self.models_file, model_row)
                result.append(
                    ModelSaleStats(
                        car_model_name=model_dict["name"],
                        brand=model_dict["brand"],
                        sales_number=stats["count"],
                    )  
                )
        return result  
