const HOST = "br.com.seuapp.infojud_bridge";
console.log("[InfoJud Bridge] Iniciando...");

let port = browser.runtime.connectNative(HOST);
console.log("connectNative done");

console.log("[InfoJud Bridge] Registering onMessage listener");

port.onMessage.addListener(async (msg) => {
  console.log("From native host:", JSON.stringify(msg));
  
  try {
    if (!msg || msg.action !== "open_url") {
      console.error("Invalid message:", msg);
      return;
    }

    const url = String(msg.url || "");
    if (!url.startsWith("http://") && !url.startsWith("https://")) {
      console.error("Invalid URL:", url);
      return;
    }

    console.log("Opening URL:", url);
    const tab = await browser.tabs.create({ url, active: true });
    console.log("Tab created:", tab.id);
  } catch (e) {
    console.error("Error opening tab:", e);
  }
});

console.log("[InfoJud Bridge] Listener registered");

port.onDisconnect.addListener(() => {
  console.log("Native host disconnected", browser.runtime.lastError);
  // NÃO reconecta automaticamente durante testes
});