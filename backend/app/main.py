from datetime import datetime, timezone
from typing import Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .zabbix import client as zabbix, ZabbixError

app = FastAPI(title="ZENTRA NOC API", description="API própria do ZENTRA NOC. Dados operacionais obtidos de integrações configuradas; sem fallback fictício.", version="0.3.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_credentials=False, allow_methods=["GET"], allow_headers=["*"])

async def zcall(method: str, params: dict):
    try:
        return await zabbix.request(method, params)
    except ZabbixError as exc:
        raise HTTPException(status_code=503, detail={"integration":"zabbix", "message":str(exc)}) from exc

def num(value: Any):
    try: return float(value)
    except (TypeError, ValueError): return None

def metric_value(items, patterns):
    for item in items:
        key = item.get("key_") or ""
        name = item.get("name") or ""
        if any(p in key.lower() or p in name.lower() for p in patterns):
            value = num(item.get("lastvalue"))
            if value is not None: return round(value, 2)
    return None

@app.get("/")
async def root(): return {"name":"ZENTRA NOC API", "version":"0.3.0", "docs":"/docs"}

@app.get("/api/health")
async def health():
    status = {"api":"online", "zabbix":"not_configured" if not settings.zabbix_url else "unknown", "wazuh":"not_configured" if not settings.wazuh_url else "configured", "timestamp":datetime.now(timezone.utc).isoformat()}
    if settings.zabbix_url:
        try:
            await zabbix.request("apiinfo.version", {})
            status["zabbix"] = "online"
        except Exception as exc:
            status["zabbix"] = "offline"
            status["zabbix_error"] = str(exc)
    return status

@app.get("/api/hosts")
async def hosts():
    raw = await zcall("host.get", {"output":["hostid","host","name","status","available","maintenance_status"], "selectInterfaces":["ip","dns","available","type"], "selectGroups":["name"], "selectTags":"extend", "sortfield":"name"})
    output=[]
    for h in raw:
        interfaces=h.get("interfaces") or []
        iface=next((x for x in interfaces if x.get("main")=="1"), interfaces[0] if interfaces else {})
        output.append({"id":h["hostid"], "name":h.get("name") or h.get("host"), "technical_name":h.get("host"), "ip":iface.get("ip") or iface.get("dns") or "—", "status":"Disabled" if h.get("status")=="1" else ("Online" if iface.get("available")=="1" else "Unknown"), "groups":[g.get("name") for g in h.get("groups",[])], "tags":h.get("tags",[]), "maintenance":h.get("maintenance_status")=="1"})
    return output

@app.get("/api/hosts/{hostid}/metrics")
async def host_metrics(hostid: str):
    await zcall("host.get", {"hostids":[hostid], "output":["hostid"]})
    items=await zcall("item.get", {"hostids":[hostid], "output":["itemid","name","key_","lastvalue","lastclock","units"], "filter":{"status":0}, "sortfield":"name"})
    cpu=metric_value(items,["system.cpu.util","cpu utilization","cpu usage"])
    mem_avail=metric_value(items,["vm.memory.size[pavailable]","memory utilization","memory used"])
    disk=metric_value(items,["vfs.fs.size[/,pused]","used space"])
    return {"hostid":hostid,"cpu_percent":cpu,"memory_available_percent":mem_avail,"disk_used_percent":disk,"items":items,"source":"zabbix","collected_at":datetime.now(timezone.utc).isoformat()}

@app.get("/api/problems")
async def problems():
    rows=await zcall("problem.get", {"output":["eventid","name","severity","clock","acknowledged","r_eventid","objectid"], "sortfield":["eventid"], "sortorder":"DESC", "selectAcknowledges":"extend", "selectTags":"extend"})
    return [{"id":p["eventid"],"title":p.get("name"),"severity":int(p.get("severity",0)),"clock":int(p.get("clock",0)),"acknowledged":p.get("acknowledged")=="1", "tags":p.get("tags",[]), "source":"Zabbix"} for p in rows]

@app.get("/api/overview")
async def overview():
    hs=await hosts(); ps=await problems()
    enabled=[h for h in hs if h["status"]!="Disabled"]
    online=sum(h["status"]=="Online" for h in enabled)
    return {"total_hosts":len(hs),"enabled_hosts":len(enabled),"online_hosts":online,"offline_or_unknown_hosts":len(enabled)-online,"active_problems":len(ps),"critical_problems":sum(p["severity"]>=4 for p in ps),"availability_percent":round(online/len(enabled)*100,1) if enabled else None,"source":"zabbix","collected_at":datetime.now(timezone.utc).isoformat()}

@app.get("/api/incidents")
async def incidents(): return await problems()

@app.get("/api/metrics")
async def metrics():
    hs=await hosts()
    return {"message":"Histórico não disponível neste endpoint. Consulte os itens/históricos do Zabbix por ativo.","hosts_with_metrics":len(hs),"source":"zabbix"}

@app.get("/api/security")
async def security():
    if not settings.wazuh_url:
        return {"connected":False,"status":"not_configured","message":"Integração Wazuh ainda não configurada. Nenhum evento de segurança será inventado.","events":[]}
    return {"connected":False,"status":"adapter_pending","message":"Endpoint Wazuh configurado; adaptador de autenticação/consulta precisa ser validado para a versão instalada.","events":[]}

@app.get("/api/topology")
async def topology():
    hs=await hosts()
    return {"source":"zabbix","nodes":hs,"edges":[],"message":"Nós obtidos do inventário Zabbix. Conexões físicas/lógicas não são inferidas sem descoberta de rede."}

@app.get("/api/reports/summary")
async def report_summary():
    data=await overview()
    return {"hosts_total":data["total_hosts"],"problems_active":data["active_problems"],"critical_problems":data["critical_problems"],"source":"zabbix","generated_at":datetime.now(timezone.utc).isoformat()}

@app.get("/api/settings")
async def get_settings():
    return {"environment":settings.app_env,"demo_mode":False,"integrations":{"zabbix":{"configured":bool(settings.zabbix_url),"url_configured":bool(settings.zabbix_url),"credentials_configured":bool(settings.zabbix_token or (settings.zabbix_user and settings.zabbix_password))},"wazuh":{"configured":bool(settings.wazuh_url)}}}
