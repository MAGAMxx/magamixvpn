import requests
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Optional, Dict
from config.servers import SERVERS_CONFIG
from config.settings import DEEPLINK_BASE
from database.models import add_subscription, update_subscription_status

class HiddifyService:
    """Сервис для работы с Hiddify серверами"""
    
    def __init__(self):
        self.servers = SERVERS_CONFIG
    
    def create_or_extend_both(self, added_days: int, user_id: int, existing_uuid: str = None) -> Optional[Dict]:
        """
        Создаёт новую подписку или продлевает существующую на ОБОИХ серверах.
        Всегда добавляет дни к текущему package_days (не заменяет).
        """
        uuid = existing_uuid or str(uuid4())
        
        # Обрабатываем оба сервера
        ru_success = self._process_server("RU", uuid, added_days, user_id, not existing_uuid)
        nl_success = self._process_server("NL", uuid, added_days, user_id, not existing_uuid)
        
        if not ru_success and not nl_success:
            print(f"Не удалось обработать ни один сервер для user={user_id}")
            return None
        
        if not ru_success:
            print(f"Предупреждение: RU сервер недоступен для user={user_id}")
        if not nl_success:
            print(f"Предупреждение: NL сервер недоступен для user={user_id}")
        
        # Если это новая подписка — сохраняем в БД
        if not existing_uuid:
            add_subscription(user_id, uuid)
        
        # Возвращаем ссылки на оба сервера
        return {
            "ru": f"{DEEPLINK_BASE}{self.servers['RU']['client_path']}/{uuid}/",
            "nl": f"{DEEPLINK_BASE}{self.servers['NL']['client_path']}/{uuid}/",
            "uuid": uuid
        }
    
    def _process_server(self, server_name: str, uuid: str, added_days: int, user_id: int, is_new: bool) -> bool:
        """Обрабатывает один сервер"""
        server = self.servers[server_name]
        headers = {"Hiddify-API-Key": server["api_key"], "Content-Type": "application/json"}
        
        if is_new:
            # Создание нового пользователя
            url = f"{server['admin_path']}/api/v2/admin/user/"
            payload = {
                "name": "",
                "package_days": added_days,
                "usage_limit_GB": 10000,
                "mode": "weekly",
                "comment": f"tg:{user_id}"
            }
            if server_name == "RU":
                payload["uuid"] = uuid  # для RU сервера можно явно указывать uuid
            
            try:
                r = requests.post(url, json=payload, headers=headers, timeout=15)
                r.raise_for_status()
                
                if server_name == "RU":
                    # RU возвращает новый uuid
                    new_uuid = r.json().get("uuid")
                    if new_uuid:
                        uuid = new_uuid
                        print(f"Создан новый пользователь на RU, uuid={uuid}")
                
                print(f"Создание на {server_name}: {added_days} дней, uuid={uuid}")
                return True
            
            except Exception as e:
                print(f"Ошибка создания на {server_name}: {e}")
                return False
        
        else:
            # Продление существующей подписки
            url = f"{server['admin_path']}/api/v2/admin/user/{uuid}/"
            try:
                r_get = requests.get(url, headers=headers, timeout=10)
                
                if r_get.status_code == 404:
                    # Пользователь не найден → создаём заново
                    print(f"Пользователь {uuid} не найден на {server_name} → создаём")
                    return self._process_server(server_name, uuid, added_days, user_id, True)
                
                r_get.raise_for_status()
                data = r_get.json()
                
                current_package = data.get("package_days", 0)
                start_date_str = data.get("start_date")
                
                # Вычисляем remaining (только для лога)
                remaining = 0
                if start_date_str and start_date_str not in ("null", "", None):
                    try:
                        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
                        expiry = start_date + timedelta(days=current_package)
                        remaining = max(0, (expiry - datetime.now()).days)
                    except ValueError as ve:
                        print(f"Неверный формат start_date '{start_date_str}' на {server_name}: {ve}")
                        remaining = 0
                else:
                    # Нет start_date → в no_reset считаем текущий пакет "оставшимся"
                    remaining = current_package if current_package > 0 else 0
                
                # Всегда добавляем дни
                new_package_days = current_package + added_days
                
                payload = {
                    "package_days": new_package_days,
                    "name": "",
                    "usage_limit_GB": 10000,
                    "mode": "weekly",
                    "comment": f"tg:{user_id}"
                }
                
                r_patch = requests.patch(url, json=payload, headers=headers, timeout=12)
                r_patch.raise_for_status()
                
                print(
                    f"Продление на {server_name}: "
                    f"{current_package} → {new_package_days} "
                    f"(remaining считался как {remaining}, start_date={start_date_str})"
                )
                return True
            
            except requests.exceptions.RequestException as req_err:
                print(f"Сетевая ошибка продления на {server_name} (uuid {uuid}): {req_err}")
                return False
            except Exception as e:
                print(f"Неизвестная ошибка продления на {server_name} (uuid {uuid}): {e}")
                return False
    
    def get_remaining_days(self, uuid: str) -> int:
        """Получает оставшиеся дни подписки (берет максимум с обоих серверов)"""
        remaining_ru = self._get_remaining_from_server(uuid, "RU")
        remaining_nl = self._get_remaining_from_server(uuid, "NL")
        
        print(f"[Remaining] uuid={uuid} → RU: {remaining_ru} дней, NL: {remaining_nl} дней")
        
        # Возвращаем максимум из двух серверов
        return max(remaining_ru, remaining_nl)
    
    def _get_remaining_from_server(self, uuid: str, server_name: str) -> int:
        """Получает оставшиеся дни с одного сервера"""
        server = self.servers[server_name]
        url = f"{server['admin_path']}/api/v2/admin/user/{uuid}/"
        headers = {"Hiddify-API-Key": server["api_key"], "Content-Type": "application/json"}
       
        try:
            r = requests.get(url, headers=headers, timeout=10)
            print(f"[GET {uuid}] Status: {r.status_code} | URL: {url}")
           
            if r.status_code != 200:
                print(f"[GET {uuid}] Не 200 → {r.text}")
                return 0
               
            data = r.json()
           
            package_days = data.get("package_days", 0)
            start_date_str = data.get("start_date")
           
            if not isinstance(package_days, (int, float)) or package_days <= 0:
                print(f"[GET {uuid}] package_days некорректный: {package_days}")
                return 0
           
            # Если start_date нет или null — считаем, что подписка свежая → возвращаем полные дни
            if not start_date_str or start_date_str in ("null", "", None):
                print(f"[GET {uuid}] Нет start_date → возвращаем полные {package_days} дней (новая подписка)")
                return int(package_days)
           
            # Пробуем распарсить дату
            start_date = None
            for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"]:
                try:
                    start_date = datetime.strptime(start_date_str, fmt)
                    break
                except ValueError:
                    continue
           
            if not start_date:
                print(f"[GET {uuid}] Неверный формат start_date: '{start_date_str}' → fallback на {package_days} дней")
                return int(package_days)
           
            # Нормальный расчёт оставшихся дней
            expiry_date = start_date + timedelta(days=package_days)
            today = datetime.now()
           
            remaining = max(0, (expiry_date - today).days)
           
            print(
                f"[GET {uuid}] server={server['admin_path'].split('//')[1].split('/')[0]} | "
                f"start={start_date.date()} | expiry≈{expiry_date.date()} | "
                f"now={today.date()} | remaining={remaining} дней"
            )
           
            return remaining
           
        except Exception as e:
            print(f"[GET {uuid}] Критическая ошибка на {server_name}: {str(e)}")
            return 0
    
    def update_comment(self, uuid: str, server_name: str, new_comment: str) -> bool:
        """Обновляет comment в Hiddify по UUID"""
        server = self.servers[server_name]
        url = f"{server['admin_path']}/api/v2/admin/user/{uuid}/"
        headers = {"Hiddify-API-Key": server["api_key"], "Content-Type": "application/json"}
        payload = {"comment": new_comment}
      
        try:
            r = requests.patch(url, json=payload, headers=headers, timeout=10)
            r.raise_for_status()
            print(f"Comment обновлён для {uuid} на {server_name}")
            return True
        except Exception as e:
            print(f"Ошибка обновления comment {uuid} на {server_name}: {e}")
            return False
    
    def delete_user(self, uuid: str, server_name: str) -> bool:
        """Удаляет пользователя в Hiddify по UUID"""
        server = self.servers[server_name]
        url = f"{server['admin_path']}/api/v2/admin/user/{uuid}/"
        headers = {"Hiddify-API-Key": server["api_key"], "Content-Type": "application/json"}
        
        try:
            r = requests.delete(url, headers=headers, timeout=10)
            if r.status_code in (200, 204, 404):  # 404 тоже ок — уже удалён
                print(f"Пользователь {uuid} удалён на {server_name}")
                return True
            else:
                print(f"Ошибка удаления {uuid} на {server_name}: {r.status_code} {r.text}")
                return False
        except Exception as e:
            print(f"Исключение при удалении {uuid} на {server_name}: {e}")
            return False
    
    def cleanup_expired_subscriptions(self, user_id: int):
        """Очищает истёкшие подписки пользователя с обоих серверов"""
        from database.models import get_user_subscriptions
        
        subs = get_user_subscriptions(user_id)
        if not subs:
            return
        
        for uuid, created_at in subs:
            created_at_dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
            age_minutes = (datetime.now() - created_at_dt).total_seconds() / 60
            
            if age_minutes < 30:
                continue
            
            remaining = self.get_remaining_days(uuid)
            if remaining <= 0:
                # Удаляем с обоих серверов
                self.delete_user(uuid, "RU")
                self.delete_user(uuid, "NL")
                update_subscription_status(uuid, "expired")
                print(f"Подписка {uuid} для user {user_id} истекла (0 дней) и удалена с обоих серверов")
