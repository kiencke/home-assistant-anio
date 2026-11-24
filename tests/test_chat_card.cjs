const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const registered = new Map();
class FakeElement {
  constructor(tagName = "") {
    this.tagName = tagName;
    this.children = [];
    this.className = "";
    this.scrollHeight = 0;
    this.scrollTop = 0;
    this.clientHeight = 0;
    this.listeners = {};
    this.classList = {
      toggle: (name, enabled) => {
        const classes = new Set(this.className.split(" ").filter(Boolean));
        if (enabled) classes.add(name);
        else classes.delete(name);
        this.className = [...classes].join(" ");
      },
    };
  }

  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  setAttribute() {}
  addEventListener(name, handler) { this.listeners[name] = handler; }
  querySelector(selector) {
    for (const child of this.children) {
      if (selector.startsWith(".") && child.className === selector.slice(1)) return child;
      if (child.tagName === selector) return child;
      const found = child.querySelector(selector);
      if (found) return found;
    }
    return null;
  }
}
const context = vm.createContext({
  HTMLElement: class {
    attachShadow() {
      this.shadowRoot = new FakeElement();
      this.statusElement = { textContent: "" };
    }
  },
  customElements: {
    get: (name) => registered.get(name),
    define: (name, element) => registered.set(name, element),
  },
  document: {
    documentElement: { lang: "en" },
    createElement: (tagName) => new FakeElement(tagName),
    visibilityState: "visible",
    addEventListener() {},
    removeEventListener() {},
  },
  window: {},
  console: { error() {} },
  setTimeout,
  clearTimeout,
  setInterval,
  clearInterval,
});
const source = readFileSync(
  path.join(__dirname, "..", "custom_components", "anio", "www", "anio-chat-card.js"),
  "utf8",
);
vm.runInContext(source, context);

function createCard(name) {
  const Card = registered.get(name);
  const card = new Card();
  card.shadowRoot = { querySelector: () => card.statusElement };
  card._config = { device_id: "ha-device" };
  card._entities = { textEntity: "text.test", messageSensor: "sensor.test" };
  card._resolveDevice = () => {};
  card.renderCount = 0;
  card._render = () => {
    card.renderCount++;
    card.statusElement.textContent = vm.runInContext("statusText", context)(card);
  };
  return card;
}

test("rendered chat controls switch languages without losing a draft", () => {
  const Card = registered.get("anio-chat-card");
  const card = new Card();
  card._config = { device_id: "ha-device" };
  card._entities = { textEntity: "text.test", messageSensor: "sensor.test" };
  card._registryLoaded = true;
  card._resolveDevice = () => {};
  const states = {
    "sensor.test": { state: "unknown", attributes: { messages: [] } },
    "text.test": { attributes: { max: 100 } },
  };
  card.hass = { locale: { language: "en" }, states };
  card._draft = "Draft";
  card.hass = { locale: { language: "de-DE" }, states };
  assert.equal(card.shadowRoot.querySelector("textarea").placeholder, "Nachricht an die Uhr");
  assert.equal(card.shadowRoot.querySelector("textarea").value, "Draft");
  assert.equal(card.shadowRoot.querySelector(".empty").textContent, "Noch keine Chatnachrichten.");
  assert.equal(card.shadowRoot.querySelector(".hint").textContent, "Sprachversand ist für dieses Gerät nicht verfügbar.");
});

test("chat card rerenders when the active locale changes without state changes", () => {
  const card = createCard("anio-chat-card");
  const states = {};
  card.hass = { locale: { language: "en-US" }, language: "de", states };
  assert.equal(card._t("send"), "Send");
  const previousRenderCount = card.renderCount;
  card.hass = { locale: { language: "de-CH" }, language: "en", states };
  assert.equal(card._t("send"), "Senden");
  assert.equal(card._t("secure"), "Für den Mikrofonzugriff ist HTTPS erforderlich.");
  assert.equal(card.renderCount, previousRenderCount + 1);
  card.hass = { locale: { language: "fr" }, states };
  assert.equal(card._t("empty"), "No chat messages yet.");
  card.hass = { states };
  assert.equal(card._t("input"), "Message the watch");
});

test("service errors use HA exception translations and update with locale", async () => {
  const card = createCard("anio-chat-card");
  const translations = {
    en: "Maximum {max_length} characters.",
    de: "Maximal {max_length} Zeichen.",
  };
  const callWS = async ({ language }) => ({
    resources: {
      "component.anio.exceptions.message_too_long.message": translations[language],
    },
  });
  const states = {};
  card.hass = { locale: { language: "en" }, callWS, states };
  card._setStatus("sendFailed", {
    message: "message_too_long",
    translation_domain: "anio",
    translation_key: "message_too_long",
    translation_placeholders: { max_length: "4" },
  });
  await new Promise(setImmediate);
  assert.equal(card.statusElement.textContent, "Message could not be sent. Maximum 4 characters.");
  card.hass = { locale: { language: "de-DE" }, callWS, states };
  await new Promise(setImmediate);
  assert.equal(
    card.statusElement.textContent,
    "Nachricht konnte nicht gesendet werden. Maximal 4 Zeichen.",
  );
  card._setStatus("");
  assert.equal(card.statusElement.textContent, "");
});

test("service error details survive missing HA translations", async () => {
  const card = createCard("anio-chat-card");
  card.hass = {
    locale: { language: "de" },
    states: {},
    callWS: async () => { throw new Error("offline"); },
  };
  card._setStatus("sendFailed", {
    message: "Original error",
    translation_domain: "anio",
    translation_key: "message_send_failed",
  });
  await new Promise(setImmediate);
  assert.equal(
    card.statusElement.textContent,
    "Nachricht konnte nicht gesendet werden. Original error",
  );
});

test("a delayed translation cannot overwrite a newer locale", async () => {
  const card = createCard("anio-chat-card");
  let resolveEnglish;
  const callWS = ({ language }) => {
    if (language === "en") {
      return new Promise((resolve) => { resolveEnglish = resolve; });
    }
    return Promise.resolve({
      resources: { "component.anio.exceptions.failed.message": "Deutscher Fehler" },
    });
  };
  card.hass = { locale: { language: "en" }, callWS, states: {} };
  card._setStatus("sendFailed", {
    message: "failed",
    translation_domain: "anio",
    translation_key: "failed",
  });
  card.hass = { locale: { language: "de" }, callWS, states: {} };
  await new Promise(setImmediate);
  resolveEnglish({
    resources: { "component.anio.exceptions.failed.message": "English error" },
  });
  await new Promise(setImmediate);
  assert.equal(
    card.statusElement.textContent,
    "Nachricht konnte nicht gesendet werden. Deutscher Fehler",
  );
});

const locationEntities = [
  ["device_tracker", "location"],
  ["button", "location_request"],
  ["button", "find_my_device"],
  ["switch", "bell_protection"],
  ["sensor", "signal_strength"],
  ["sensor", "battery"],
  ["sensor", "location_request_status"],
  ["sensor", "last_location"],
  ["sensor", "last_response"],
  ["sensor", "gps_accuracy"],
  ["sensor", "position_source"],
  ["switch", "explorer"],
  ["switch", "radar_mode"],
];

function locationHass(deviceId, options = {}) {
  const entries = locationEntities
    .filter(([, suffix]) => suffix !== options.omit)
    .map(([domain, suffix]) => ({
      device_id: deviceId, platform: "anio",
      unique_id: `watch_${suffix}`, entity_id: `${domain}.${deviceId}_${suffix}`,
    }));
  return {
    locale: { language: options.language || "en" },
    states: { [`switch.${deviceId}_bell_protection`]: { state: options.protection || "off" } },
    callWS: async ({ type }) => type === "config/device_registry/list"
      ? [{ id: deviceId, identifiers: [["anio", deviceId]] }]
      : entries,
  };
}

function installCardHelpers() {
  const created = [];
  const create = (kind) => (config) => {
    const element = new FakeElement(kind);
    element.config = config;
    element.setConfig = (updated) => { element.config = updated; };
    created.push(element);
    return element;
  };
  context.window.loadCardHelpers = async () => ({
    createCardElement: create("card"), createBadgeElement: create("badge"),
  });
  return created;
}

test("location card creates native badges and cards and updates them without rebuilding", async () => {
  const created = installCardHelpers();
  const card = new (registered.get("anio-location-card"))();
  card.setConfig({ device_id: "watch" });
  const hass = locationHass("watch");
  card.hass = hass;
  await new Promise(setImmediate);
  const badges = created.filter((element) => element.tagName === "badge");
  assert.deepEqual(badges.map((element) => element.config.entity), [
    "sensor.watch_signal_strength", "sensor.watch_position_source",
    "sensor.watch_gps_accuracy", "sensor.watch_battery",
  ]);
  assert.ok(badges.every((element) => !element.config.show_name && element.config.show_state && element.config.show_icon));
  const map = created.find((element) => element.config.type === "map");
  assert.equal(map.config.entities[0].entity, "device_tracker.watch_location");
  assert.equal(map.config.entities[0].color, "indigo");
  assert.equal(map.config.entities[0].label_mode, "icon");
  assert.equal(map.config.theme_mode, "auto");
  const request = created.find((element) => element.config.type === "button");
  assert.equal(request.config.tap_action.perform_action, "button.press");
  assert.equal(request.config.tap_action.target.entity_id, "button.watch_location_request");
  assert.deepEqual(
    created.filter((element) => element.config.type === "tile")
      .map((element) => element.config.entity),
    [
      "device_tracker.watch_location", "sensor.watch_location_request_status",
      "sensor.watch_last_response", "switch.watch_explorer",
      "sensor.watch_last_location", "switch.watch_radar_mode",
      "button.watch_find_my_device", "switch.watch_bell_protection",
    ],
  );
  const ring = created.find((element) => element.config.entity === "button.watch_find_my_device");
  assert.equal(ring.config.icon_tap_action.perform_action, "button.press");
  assert.equal(ring.config.tap_action.target.entity_id, "button.watch_find_my_device");
  const protection = created.find((element) => element.config.entity === "switch.watch_bell_protection");
  assert.equal(protection.config.features[0].type, "toggle");
  assert.equal(protection.config.icon, "mdi:shield-lock");
  assert.deepEqual(
    created.filter((element) => element.config.type === "button" || element.config.type === "tile")
      .map((element) => element.config.name),
    [
      "Request location", "", "Location request status", "Last response", "Explorer",
      "Position update", "Radar mode", "Ring watch", "Bell protection",
    ],
  );
  assert.equal(card._ringWrapper.inert, false);
  const updated = locationHass("watch", { language: "de-DE", protection: "on" });
  card.hass = updated;
  assert.equal(card._labels.location.textContent, "Standort");
  assert.equal(card._labels.functions.textContent, "Weitere Funktionen");
  assert.equal(card._labels.protection.textContent, "Klingel-Schutz ist aktiv.");
  assert.equal(card._ringWrapper.inert, true);
  assert.deepEqual(
    created.filter((element) => element.config.type === "button" || element.config.type === "tile")
      .map((element) => element.config.name),
    [
      "Standort anfordern", "", "Status Standortanforderung", "Letzte Antwort", "Explorer",
      "Positions-Update", "Radar-Modus", "Uhr klingeln lassen", "Klingel-Schutz",
    ],
  );
  assert.equal(map.hass, updated);
  assert.equal(created.filter((element) => element.config.type === "map").length, 1);
  card.hass = locationHass("watch", { protection: "unknown" });
  assert.equal(card._ringWrapper.inert, true);
  assert.equal(card._labels.protection.textContent, "Bell protection is unavailable.");
  assert.equal(ring.config.name, "Ring watch");
  assert.equal(ring.config.tap_action.target.entity_id, "button.watch_find_my_device");
});

test("location card reports missing entities and disables ringing without protection", async () => {
  installCardHelpers();
  const card = new (registered.get("anio-location-card"))();
  card.setConfig({ device_id: "watch" });
  card.hass = locationHass("watch", { omit: "bell_protection", language: "de" });
  await new Promise(setImmediate);
  assert.match(card._labels.missing.textContent, /Klingel-Schutz/);
  assert.equal(card._ringWrapper.inert, true);
});

test("location card ignores stale device results and reports load errors", async () => {
  installCardHelpers();
  const card = new (registered.get("anio-location-card"))();
  let release;
  const delayed = locationHass("first");
  const callWS = delayed.callWS;
  delayed.callWS = (request) => new Promise((resolve) => {
    if (request.type === "config/device_registry/list") release = () => callWS(request).then(resolve);
    else callWS(request).then(resolve);
  });
  card.setConfig({ device_id: "first" });
  card.hass = delayed;
  card.hass = locationHass("second");
  card.setConfig({ device_id: "second" });
  await new Promise(setImmediate);
  release();
  await new Promise(setImmediate);
  assert.equal(card._entities.location, "device_tracker.second_location");

  const failed = new (registered.get("anio-location-card"))();
  failed.setConfig({ device_id: "watch" });
  failed.hass = { locale: { language: "de" }, callWS: async () => { throw new Error("offline"); } };
  await new Promise(setImmediate);
  assert.equal(failed._labels.state.textContent, "Die Standortkarte konnte nicht geladen werden.");
});

function activityHass(language, activities, state = "geofence_entered") {
  return {
    locale: { language },
    config: { time_zone: "UTC" },
    states: { "sensor.watch_activity": { state, attributes: { activities } } },
    callWS: async ({ type }) => type === "config/device_registry/list"
      ? [{ id: "watch", identifiers: [["anio", "watch-1"]] }]
      : [{ device_id: "watch", platform: "anio", unique_id: "watch-1_last_activity", entity_id: "sensor.watch_activity" }],
  };
}

test("activity card resolves the watch and renders localized zones and unknown types", async () => {
  const card = new (registered.get("anio-activity-card"))();
  card.setConfig({ device_id: "watch" });
  const activities = [
    { type: "GEOFENCE_ENTERED", zone: "Schule", display_timestamp: "2026-01-02T08:15:00Z" },
    { type: "GEOFENCE_LEFT", zone: "Zuhause", display_timestamp: "2026-01-02T08:14:00Z" },
    { type: "LOW_BATTERY", display_timestamp: "2026-01-02T07:30:00Z" },
    { type: "NEW_EVENT", text: "<unbekannt>", display_timestamp: "2026-01-02T07:00:00Z" },
  ];
  card.hass = activityHass("de-DE", activities);
  await new Promise(setImmediate);
  let rows = card.shadowRoot.querySelector(".activities").children;
  assert.equal(card._entities.activitySensor, "sensor.watch_activity");
  assert.equal(rows[0].children[1].children[0].textContent, "Schule betreten");
  assert.equal(rows[0].children[1].children[1].textContent, "Anio-Zone");
  assert.equal(rows[1].children[1].children[0].textContent, "Zuhause verlassen");
  assert.equal(rows[1].children[1].children[1].textContent, "Anio-Zone · Zeitpunkt geschätzt");
  assert.match(rows[1].children[2].textContent, /08:14/);
  assert.equal(rows[2].children[1].children[0].textContent, "Akku fast leer");
  assert.equal(rows[2].children[1].children.length, 1);
  assert.equal(rows[3].children[1].children[0].textContent, "<unbekannt>");
  card.hass = activityHass("en-US", activities);
  rows = card.shadowRoot.querySelector(".activities").children;
  assert.equal(rows[0].children[1].children[0].textContent, "Entered Schule");
  assert.equal(rows[0].children[1].children[1].textContent, "Anio zone");
  assert.equal(rows[1].children[1].children[1].textContent, "Anio zone · Estimated time");
  assert.equal(rows[2].children[1].children[0].textContent, "Battery low");
});

test("activity card displays empty and failed states", async () => {
  const card = new (registered.get("anio-activity-card"))();
  card.setConfig({ device_id: "watch" });
  card.hass = activityHass("en", [], "unknown");
  await new Promise(setImmediate);
  assert.equal(card.shadowRoot.querySelector(".empty").textContent, "No activities yet.");
  card.hass = activityHass("de", [], "unavailable");
  assert.equal(card.shadowRoot.querySelector(".empty").textContent, "Aktivitäten konnten nicht aktualisiert werden.");
  const retained = activityHass("de", [
    { type: "LOW_BATTERY", display_timestamp: "2026-01-02T07:30:00Z" },
  ]);
  card.hass = retained;
  retained.states["sensor.watch_activity"].attributes.update_available = false;
  card.hass = retained;
  const rows = card.shadowRoot.querySelector(".activities").children;
  assert.equal(rows[0].textContent, "Aktivitäten konnten nicht aktualisiert werden.");
  assert.equal(rows[1].children[1].children[0].textContent, "Akku fast leer");
});

test("activity card refreshes on visibility and exposes a manual refresh button", async () => {
  let observer;
  let visibilityHandler;
  context.document.addEventListener = (name, handler) => {
    if (name === "visibilitychange") visibilityHandler = handler;
  };
  context.document.removeEventListener = (name, handler) => {
    if (name === "visibilitychange" && visibilityHandler === handler) visibilityHandler = null;
  };
  context.IntersectionObserver = class {
    constructor(callback) { this.callback = callback; observer = this; }
    observe() {}
    disconnect() { this.disconnected = true; }
  };
  const calls = [];
  let release;
  const hass = activityHass("de", [], "unknown");
  hass.callService = (...args) => {
    calls.push(args);
    return new Promise((resolve) => { release = resolve; });
  };
  const card = new (registered.get("anio-activity-card"))();
  card.connectedCallback();
  card.setConfig({ device_id: "watch" });
  card.hass = hass;
  await new Promise(setImmediate);
  assert.equal(calls.length, 0);
  observer.callback([{ isIntersecting: true }]);
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], "anio");
  assert.equal(calls[0][1], "refresh_activities");
  assert.equal(calls[0][2].force, false);
  assert.equal(card.shadowRoot.querySelector(".refresh").disabled, true);
  assert.equal(card.shadowRoot.querySelector(".refresh").textContent, "Aktualisiere …");
  release();
  await new Promise(setImmediate);
  const button = card.shadowRoot.querySelector(".refresh");
  assert.equal(button.disabled, false);
  assert.equal(button.textContent, "Aktualisieren");
  button.listeners.click();
  assert.equal(calls[1][2].force, true);
  release();
  await new Promise(setImmediate);
  context.document.visibilityState = "hidden";
  visibilityHandler();
  assert.equal(calls.length, 2);
  context.document.visibilityState = "visible";
  visibilityHandler();
  assert.equal(calls[2][2].force, false);
  release();
  await new Promise(setImmediate);
  card.disconnectedCallback();
  assert.equal(observer.disconnected, true);
  assert.equal(visibilityHandler, null);
  delete context.IntersectionObserver;
});

test("activity card displays a failed manual refresh", async () => {
  const card = new (registered.get("anio-activity-card"))();
  card.setConfig({ device_id: "watch" });
  const hass = activityHass("en", [], "unknown");
  hass.callService = async () => { throw new Error("offline"); };
  card.hass = hass;
  await new Promise(setImmediate);
  card.shadowRoot.querySelector(".refresh").listeners.click();
  await new Promise(setImmediate);
  assert.equal(card.shadowRoot.querySelector(".empty").textContent, "Could not update activities.");
});
