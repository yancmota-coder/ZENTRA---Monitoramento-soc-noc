import itertools
import httpx
from .config import settings

class ZabbixError(RuntimeError):
    pass

class ZabbixClient:
    def __init__(self):
        self._ids = itertools.count(1)

    async def call(self, method: str, params: dict):
        if not settings.zabbix_url:
            raise ZabbixError("ZABBIX_URL não configurada")
        payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": next(self._ids)}
        headers = {"Content-Type": "application/json-rpc"}
        if settings.zabbix_token:
            headers["Authorization"] = f"Bearer {settings.zabbix_token}"
        async with httpx.AsyncClient(timeout=settings.zabbix_timeout, verify=settings.zabbix_verify_tls) as client:
            try:
                response = await client.post(settings.zabbix_url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                raise ZabbixError(f"Falha de comunicação com Zabbix: {exc}") from exc
        if data.get("error"):
            err = data["error"]
            raise ZabbixError(err.get("data") or err.get("message") or "Erro JSON-RPC do Zabbix")
        return data.get("result")

    async def request(self, method: str, params: dict):
        if not settings.zabbix_token:
            if not settings.zabbix_user or not settings.zabbix_password:
                raise ZabbixError("Configure ZABBIX_TOKEN ou ZABBIX_USER/ZABBIX_PASSWORD")
            token = await self.call("user.login", {"username": settings.zabbix_user, "password": settings.zabbix_password})
            payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": next(self._ids)}
            async with httpx.AsyncClient(timeout=settings.zabbix_timeout, verify=settings.zabbix_verify_tls) as client:
                response = await client.post(settings.zabbix_url, json=payload, headers={"Content-Type":"application/json-rpc", "Authorization": f"Bearer {token}"})
                response.raise_for_status()
                data = response.json()
            if data.get("error"):
                err = data["error"]
                raise ZabbixError(err.get("data") or err.get("message") or "Erro JSON-RPC do Zabbix")
            return data.get("result")
        return await self.call(method, params)

client = ZabbixClient()
