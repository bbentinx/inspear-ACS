// Provision GenieACS — coleta TR-069 + restore remoto pós-reset (Inspear ACS)
// Instalar: make setup-genieacs

const INSPEAR_URL = "http://api:8000/api/v1/acs/genieacs/webhook";
const INSPEAR_PROVISION_URL = "http://api:8000/api/v1/acs/provision";
const INSPEAR_API_KEY = "inspear-dev-key";

const now = Date.now();

const PARAMS = [
  "InternetGatewayDevice.DeviceInfo.SerialNumber",
  "InternetGatewayDevice.DeviceInfo.Manufacturer",
  "InternetGatewayDevice.DeviceInfo.ModelName",
  "InternetGatewayDevice.DeviceInfo.SoftwareVersion",
  "InternetGatewayDevice.DeviceInfo.UpTime",
  "InternetGatewayDevice.ManagementServer.URL",
  "InternetGatewayDevice.ManagementServer.Username",
  "InternetGatewayDevice.WANDevice.1.X_GponInterafceConfig.RXPower",
  "InternetGatewayDevice.WANDevice.1.X_GponInterafceConfig.TXPower",
  "InternetGatewayDevice.WANDevice.1.X_GponInterafceConfig.TransceiverTemperature",
  "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.ConnectionStatus",
  "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.Username",
  "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.ExternalIPAddress",
  "InternetGatewayDevice.WANDevice.1.WANConnectionDevice.1.WANPPPConnection.1.X_HW_VLAN",
  "InternetGatewayDevice.LANDevice.1.LANEthernetInterfaceConfig.1.Status",
  "InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.TotalAssociations",
  "InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.SSID",
  "InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.Channel",
  "InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.BeaconType",
  "InternetGatewayDevice.LANDevice.1.WLANConfiguration.1.AssociatedDevice",
  "InternetGatewayDevice.LANDevice.1.WLANConfiguration.5.TotalAssociations",
  "InternetGatewayDevice.LANDevice.1.WLANConfiguration.5.SSID",
  "InternetGatewayDevice.LANDevice.1.WLANConfiguration.5.Channel",
  "InternetGatewayDevice.LANDevice.1.WLANConfiguration.5.BeaconType",
  "InternetGatewayDevice.LANDevice.1.WLANConfiguration.5.AssociatedDevice",
  "InternetGatewayDevice.DownloadDiagnostics.DiagnosticsState",
  "InternetGatewayDevice.DownloadDiagnostics.TestBytesReceived",
  "InternetGatewayDevice.UploadDiagnostics.DiagnosticsState",
  "InternetGatewayDevice.UploadDiagnostics.TotalBytesSent",
  "InternetGatewayDevice.DeviceInfo.X_HW_CpuUsage",
  "InternetGatewayDevice.DeviceInfo.X_HW_MemoryUsage",
  "InternetGatewayDevice.DeviceInfo.X_HW_CpuUsed",
  "InternetGatewayDevice.DeviceInfo.X_HW_MemUsed",
];

for (const p of PARAMS) {
  declare(p, {value: now});
}

const event = String(args[0] || "");

// BOOTSTRAP / BOOT — reaplica perfil salvo (só funciona se ONT já alcança o ACS)
const isBootEvent =
  event.indexOf("BOOTSTRAP") >= 0 ||
  event.indexOf("BOOT") >= 0 ||
  event === "1 BOOT" ||
  event === "0 BOOTSTRAP";

if (isBootEvent) {
  const serial = declare("InternetGatewayDevice.DeviceInfo.SerialNumber", {value: 1})[0];
  if (serial) {
    try {
      const res = http.request({
        method: "GET",
        uri: INSPEAR_PROVISION_URL + "/" + serial,
        headers: {"X-API-Key": INSPEAR_API_KEY},
      });
      if (res && res.statusCode === 200 && res.body) {
        const cfg = JSON.parse(res.body);
        if (cfg.parameters) {
          for (const item of cfg.parameters) {
            if (item.path && item.value !== undefined && item.value !== null && item.value !== "") {
              const opts = {value: item.value};
              if (item.type) opts.type = item.type;
              declare(item.path, opts);
            }
          }
          log("Inspear restore " + event + ": " + cfg.parameters.length + " params para " + serial);
        }
        http.request({
          method: "POST",
          uri: INSPEAR_PROVISION_URL + "/" + serial + "/apply",
          headers: {"X-API-Key": INSPEAR_API_KEY},
        });
      }
    } catch (e) {
      log("Inspear restore BOOT error: " + e);
    }
  }
}

// Inform periódico — encaminha para Inspear
if (event.indexOf("PERIODIC") >= 0 || event.indexOf("BOOT") >= 0 || event.indexOf("VALUE CHANGE") >= 0) {
  const deviceDoc = {};
  for (const p of PARAMS) {
    const val = declare(p, {value: 1});
    if (val && val[0] !== undefined) deviceDoc[p] = val[0];
  }
  deviceDoc._id = declare("InternetGatewayDevice.DeviceInfo.SerialNumber", {value: 1})[0] || serial;
  deviceDoc._lastInform = new Date().toISOString();
  if (event) deviceDoc._event = event;

  try {
    http.request({
      method: "POST",
      uri: INSPEAR_URL,
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": INSPEAR_API_KEY,
      },
      body: JSON.stringify(deviceDoc),
    });
  } catch (e) {
    log("Inspear webhook error: " + e);
  }
}