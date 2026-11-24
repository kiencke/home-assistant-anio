const EMOJIS = [
  ["E01", "🙂"],
  ["E02", "😘"],
  ["E03", "😎"],
  ["E04", "🙁"],
  ["E05", "😁"],
  ["E06", "😛"],
  ["E07", "👎"],
  ["E08", "👍"],
  ["E09", "❤️"],
];

const TRANSLATIONS = {
  de: {
    empty: "Noch keine Chatnachrichten.",
    loading: "Anio-Gerät wird geladen …",
    registryError: "Anio-Gerät oder Entitäten konnten nicht geladen werden.",
    noChat: "Für dieses Gerät ist kein Chat verfügbar.",
    refreshFailed: "Chat konnte nicht aktualisiert werden.",
    input: "Nachricht an die Uhr",
    send: "Senden",
    emoji: "Emoji senden",
    microphone: "Sprachnachricht aufnehmen",
    stop: "Aufnahme beenden",
    secure: "Für den Mikrofonzugriff ist HTTPS erforderlich.",
    unsupported: "Mikrofonaufnahme wird von diesem Browser nicht unterstützt.",
    missingDevice: "Sprachversand ist für dieses Gerät nicht verfügbar.",
    recordingPending: "Die Aufnahme wird vorbereitet; das Anio-Audioformat ist noch nicht verifiziert.",
    recordingTooLong: "Aufnahme nach 30 Sekunden beendet.",
    watch: "Uhr",
    homeAssistant: "Home Assistant",
    sendFailed: "Nachricht konnte nicht gesendet werden.",
    emojiFailed: "Emoji konnte nicht gesendet werden.",
    recordFailed: "Aufnahme konnte nicht gestartet werden.",
    audioFailed: "Audio konnte nicht geladen werden.",
    voiceNotReady: "Sprachversand ist noch nicht verfügbar.",
    deviceNotFound: "Anio-Gerät wurde nicht gefunden.",
    voiceMessageNotFound: "Sprachnachricht wurde nicht gefunden.",
    voiceSourceNotVerified: "Die Anio-Audioquelle ist noch nicht verifiziert.",
    voiceChatUnsupported: "Dieses Anio-Gerät unterstützt keinen Sprachchat.",
    audioRequired: "Der Upload muss einen Audio-Content-Type verwenden.",
    audioTooLarge: "Die Audiodatei überschreitet die maximale Größe.",
    voiceFormatNotConfigured: "Audioformat und Upload-API sind noch nicht verifiziert.",
    voiceUploadNotImplemented: "Der Anio-Audio-Upload ist noch nicht implementiert.",
    voiceMessage: "Sprachnachricht",
    device: "Anio-Gerät",
    locationHeading: "Standort",
    functionsHeading: "Weitere Funktionen",
    locationCardError: "Die Standortkarte konnte nicht geladen werden.",
    missingEntities: "Einige Entitäten sind nicht verfügbar",
    networkQuality: "Netzqualität",
    positionSource: "Ortungsquelle",
    gpsAccuracy: "GPS-Genauigkeit",
    battery: "Akku",
    location: "Standort",
    requestLocation: "Standort anfordern",
    locationRequestStatus: "Status Standortanforderung",
    lastResponse: "Letzte Antwort",
    explorer: "Explorer",
    lastLocation: "Positions-Update",
    radarMode: "Radar-Modus",
    ringWatch: "Uhr klingeln lassen",
    bellProtectionOn: "Klingel-Schutz ist aktiv.",
    bellProtectionUnavailable: "Klingel-Schutz ist nicht verfügbar.",
    bellProtection: "Klingel-Schutz",
    activitiesHeading: "Aktivitäten",
    noActivities: "Noch keine Aktivitäten.",
    activityUnavailable: "Aktivitäten konnten nicht aktualisiert werden.",
    noActivitySensor: "Der Aktivitätssensor ist nicht verfügbar.",
    anioZone: "Anio-Zone",
    unknownZone: "Unbekannte Zone",
    enteredZone: "{zone} betreten",
    leftZone: "{zone} verlassen",
    lowBattery: "Akku fast leer",
    estimatedDeparture: "Geschätzter Zeitpunkt: eine Minute vor dem Anio-Zeitstempel.",
    estimatedTime: "Zeitpunkt geschätzt",
    refreshActivities: "Aktualisieren",
    refreshingActivities: "Aktualisiere …",
  },
  en: {
    empty: "No chat messages yet.",
    loading: "Loading Anio device …",
    registryError: "Could not load the Anio device or its entities.",
    noChat: "Chat is not available for this device.",
    refreshFailed: "Could not refresh the chat.",
    input: "Message the watch",
    send: "Send",
    emoji: "Send emoji",
    microphone: "Record voice message",
    stop: "Stop recording",
    secure: "HTTPS is required to access the microphone.",
    unsupported: "Microphone recording is not supported by this browser.",
    missingDevice: "Voice sending is not available for this device.",
    recordingPending: "Recording is prepared; the Anio audio format is not verified yet.",
    recordingTooLong: "Recording stopped after 30 seconds.",
    watch: "Watch",
    homeAssistant: "Home Assistant",
    sendFailed: "Message could not be sent.",
    emojiFailed: "Emoji could not be sent.",
    recordFailed: "Recording could not be started.",
    audioFailed: "Audio could not be loaded.",
    voiceNotReady: "Voice sending is not available yet.",
    deviceNotFound: "The Anio device was not found.",
    voiceMessageNotFound: "The voice message was not found.",
    voiceSourceNotVerified: "The Anio audio source has not been verified yet.",
    voiceChatUnsupported: "This Anio device does not support voice chat.",
    audioRequired: "The upload must use an audio content type.",
    audioTooLarge: "The audio file exceeds the maximum size.",
    voiceFormatNotConfigured: "The audio format and upload API have not been verified.",
    voiceUploadNotImplemented: "The Anio audio upload has not been implemented yet.",
    voiceMessage: "Voice message",
    device: "Anio device",
    locationHeading: "Location",
    functionsHeading: "More Functions",
    locationCardError: "Could not load the location card.",
    missingEntities: "Some entities are not available",
    networkQuality: "Network quality",
    positionSource: "Position source",
    gpsAccuracy: "GPS accuracy",
    battery: "Battery",
    location: "Location",
    requestLocation: "Request location",
    locationRequestStatus: "Location request status",
    lastResponse: "Last response",
    explorer: "Explorer",
    lastLocation: "Position update",
    radarMode: "Radar mode",
    ringWatch: "Ring watch",
    bellProtectionOn: "Bell protection is enabled.",
    bellProtectionUnavailable: "Bell protection is unavailable.",
    bellProtection: "Bell protection",
    activitiesHeading: "Activities",
    noActivities: "No activities yet.",
    activityUnavailable: "Could not update activities.",
    noActivitySensor: "The activity sensor is not available.",
    anioZone: "Anio zone",
    unknownZone: "Unknown zone",
    enteredZone: "Entered {zone}",
    leftZone: "Left {zone}",
    lowBattery: "Battery low",
    estimatedDeparture: "Estimated time: one minute before the Anio timestamp.",
    estimatedTime: "Estimated time",
    refreshActivities: "Refresh",
    refreshingActivities: "Refreshing …",
  },
};

function translate(hass, key) {
  const language = hass?.locale?.language?.toLowerCase().startsWith("de")
    ? "de"
    : "en";
  return TRANSLATIONS[language][key] || TRANSLATIONS.en[key] || key;
}

function statusText(card) {
  if (!card._status) return "";
  const message = translate(card._hass, card._status);
  return card._statusDetail ? `${message} ${card._statusDetail}` : message;
}

async function updateStatusDetail(card) {
  const error = card._statusError;
  const sequence = (card._statusSequence || 0) + 1;
  card._statusSequence = sequence;
  card._statusDetail = "";
  const currentStatus = card.shadowRoot.querySelector(".status");
  if (currentStatus) currentStatus.textContent = statusText(card);
  let detail = error?.message || "";
  if (error?.translation_domain && error?.translation_key && card._hass) {
    try {
      const language = card._hass.locale?.language?.toLowerCase().startsWith("de")
        ? "de"
        : "en";
      const result = await card._hass.callWS({
        type: "frontend/get_translations",
        language,
        category: "exceptions",
        integration: error.translation_domain,
      });
      const key = `component.${error.translation_domain}.exceptions.${error.translation_key}.message`;
      const translated = result.resources?.[key];
      if (typeof translated === "string") {
        detail = translated.replace(/\{([^{}]+)\}/g, (match, name) =>
          error.translation_placeholders?.[name] ?? match,
        );
      }
    } catch (translationError) {
      console.error("Could not load Home Assistant error translations:", translationError);
    }
  }
  if (sequence !== card._statusSequence) return;
  card._statusDetail = detail;
  const status = card.shadowRoot.querySelector(".status");
  if (status) status.textContent = statusText(card);
}

function setCardStatus(card, key, error = null) {
  card._status = key;
  card._statusError = error;
  updateStatusDetail(card);
}

const registryCache = new WeakMap();
const VOICE_ERROR_STRINGS = {
  device_not_found: "deviceNotFound",
  voice_message_not_found: "voiceMessageNotFound",
  voice_source_not_verified: "voiceSourceNotVerified",
  voice_chat_unsupported: "voiceChatUnsupported",
  audio_required: "audioRequired",
  audio_too_large: "audioTooLarge",
  voice_format_not_configured: "voiceFormatNotConfigured",
  voice_upload_not_implemented: "voiceUploadNotImplemented",
};

function getAnioRegistry(hass) {
  let registryPromise = registryCache.get(hass);
  if (!registryPromise) {
    registryPromise = Promise.all([
      hass.callWS({ type: "config/device_registry/list" }),
      hass.callWS({ type: "config/entity_registry/list" }),
    ]).then(([devices, entities]) => ({ devices, entities }));
    registryCache.set(hass, registryPromise);
  }
  return registryPromise;
}

async function resolveAnioDevice(hass, deviceId) {
  const { devices, entities } = await getAnioRegistry(hass);
  const device = devices.find((item) => item.id === deviceId);
  const identifier = device?.identifiers?.find(([domain]) => domain === "anio");
  if (!device || !identifier) {
    throw new Error("Anio device was not found in the Home Assistant device registry.");
  }

  const deviceEntities = entities.filter(
    (entity) => entity.device_id === deviceId && entity.platform === "anio",
  );
  const findEntity = (domain, uniqueIdSuffix) =>
    deviceEntities.find(
      (entity) =>
        entity.entity_id.startsWith(`${domain}.`) &&
        entity.unique_id.endsWith(`_${uniqueIdSuffix}`),
    )?.entity_id;

  return {
    name: device.name_by_user || device.name || "",
    anioDeviceId: identifier[1],
    location: findEntity("device_tracker", "location"),
    locationRequest: findEntity("button", "location_request"),
    findMyDevice: findEntity("button", "find_my_device"),
    bellProtection: findEntity("switch", "bell_protection"),
    signalStrength: findEntity("sensor", "signal_strength"),
    battery: findEntity("sensor", "battery"),
    locationRequestStatus: findEntity("sensor", "location_request_status"),
    lastLocation: findEntity("sensor", "last_location"),
    lastResponse: findEntity("sensor", "last_response"),
    gpsAccuracy: findEntity("sensor", "gps_accuracy"),
    positionSource: findEntity("sensor", "position_source"),
    explorer: findEntity("switch", "explorer"),
    radarMode: findEntity("switch", "radar_mode"),
    textEntity: findEntity("text", "send_message"),
    messageSensor: findEntity("sensor", "last_message"),
    activitySensor: findEntity("sensor", "last_activity"),
  };
}

class AnioDeviceCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  setConfig(config) {
    this._config = config;
    this._render();
  }

  _render() {
    if (!this._hass) return;
    const root = this.shadowRoot;
    root.replaceChildren();

    const label = document.createElement("div");
    label.textContent = translate(this._hass, "device");
    const form = document.createElement("ha-form");
    form.hass = this._hass;
    form.data = { device_id: this._config?.device_id || "" };
    form.schema = [
      {
        name: "device_id",
        required: true,
        selector: { device: { integration: "anio" } },
      },
    ];
    form.addEventListener("value-changed", (event) => {
      const deviceId = event.detail.value.device_id;
      if (!deviceId) return;
      this._config = { ...this._config, device_id: deviceId };
      delete this._config.text_entity;
      delete this._config.message_sensor;
      delete this._config.voice_device_id;
      this.dispatchEvent(
        new CustomEvent("config-changed", {
          detail: { config: this._config },
          bubbles: true,
          composed: true,
        }),
      );
    });
    root.append(label, form);
  }
}

if (!customElements.get("anio-device-card-editor")) {
  customElements.define("anio-device-card-editor", AnioDeviceCardEditor);
}

class AnioChatCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._draft = "";
    this._status = "";
    this._signature = "";
    this._recorder = null;
    this._recordingTimeout = null;
    this._discardRecording = false;
    this._chatVisible = false;
    this._refreshInterval = null;
    this._refreshInProgress = false;
    this._visibilityChangeHandler = () => this._updateRefreshPolling();
  }

  connectedCallback() {
    document.addEventListener("visibilitychange", this._visibilityChangeHandler);
    if (typeof IntersectionObserver === "function") {
      this._visibilityObserver = new IntersectionObserver((entries) => {
        this._chatVisible = entries.some((entry) => entry.isIntersecting);
        this._updateRefreshPolling();
      });
      this._visibilityObserver.observe(this);
    } else {
      this._chatVisible = true;
      this._updateRefreshPolling();
    }
  }

  disconnectedCallback() {
    clearTimeout(this._recordingTimeout);
    clearInterval(this._refreshInterval);
    this._refreshInterval = null;
    this._visibilityObserver?.disconnect();
    this._visibilityObserver = null;
    document.removeEventListener("visibilitychange", this._visibilityChangeHandler);
    if (this._recorder && this._recorder.state !== "inactive") {
      this._discardRecording = true;
      this._recorder.stop();
    }
  }

  setConfig(config) {
    if (!config?.device_id) {
      throw new Error(
        "anio-chat-card requires an Anio device.",
      );
    }
    this._config = config;
    this._entities = {
      textEntity: config.text_entity,
      messageSensor: config.message_sensor,
      anioDeviceId: config.voice_device_id,
    };
    this._registryLoaded = false;
    this._registryError = "";
    if (this._entities.textEntity && this._entities.messageSensor) {
      this._registryLoaded = true;
    }
    this._resolveDevice();
    this._signature = "";
    this._render();
    this._updateRefreshPolling();
    if (this._chatVisible) this._refreshChat();
  }

  set hass(hass) {
    const firstHass = !this._hass;
    const languageChanged = this._hass?.locale?.language !== hass.locale?.language;
    this._hass = hass;
    if (!this._config) return;
    this._resolveDevice();
    if (firstHass && this._chatVisible) this._refreshChat();
    const sensor = hass.states?.[this._entities?.messageSensor];
    const textEntity = hass.states?.[this._entities?.textEntity];
    const signature = JSON.stringify([
      hass.locale?.language,
      sensor?.state,
      sensor?.attributes?.messages,
      textEntity?.attributes?.max,
    ]);
    if (signature !== this._signature) {
      this._signature = signature;
      this._render();
    }
    if (languageChanged && this._status) updateStatusDetail(this);
  }

  static getConfigElement() {
    return document.createElement("anio-device-card-editor");
  }

  static getStubConfig() {
    return { device_id: "" };
  }

  _resolveDevice() {
    if (
      !this._hass ||
      !this._config?.device_id ||
      (this._entities?.textEntity && this._entities?.messageSensor) ||
      this._registryLoaded ||
      this._resolving
    ) {
      return;
    }
    this._resolving = true;
    resolveAnioDevice(this._hass, this._config.device_id)
      .then((entities) => {
        this._entities = {
          ...entities,
          textEntity: this._config.text_entity || entities.textEntity,
          messageSensor: this._config.message_sensor || entities.messageSensor,
          anioDeviceId: this._config.voice_device_id || entities.anioDeviceId,
        };
        this._registryLoaded = true;
        this._registryError = "";
      })
      .catch((error) => {
        console.error("Could not resolve the Anio device:", error);
        this._registryLoaded = true;
        this._registryError = true;
      })
      .finally(() => {
        this._resolving = false;
        this._render();
      });
  }

  _updateRefreshPolling() {
    const active =
      this.isConnected &&
      this._chatVisible &&
      document.visibilityState === "visible";
    if (!active) {
      clearInterval(this._refreshInterval);
      this._refreshInterval = null;
      return;
    }
    if (this._refreshInterval) return;
    this._refreshChat();
    this._refreshInterval = setInterval(() => this._refreshChat(), 30000);
  }

  async _refreshChat() {
    if (!this._hass || !this._config?.device_id || this._refreshInProgress) return;
    this._refreshInProgress = true;
    try {
      await this._hass.callService("anio", "refresh_chat", {
        device_id: this._config.device_id,
      });
    } catch (error) {
      console.error("Could not refresh Anio chat:", error);
      this._setStatus("refreshFailed", error);
    } finally {
      this._refreshInProgress = false;
    }
  }

  getCardSize() {
    return 5;
  }

  _t(key) {
    return translate(this._hass, key);
  }

  _render() {
    if (!this._config) return;
    const sensor = this._hass?.states?.[this._entities?.messageSensor];
    const textEntity = this._hass?.states?.[this._entities?.textEntity];
    const messages = sensor?.attributes?.messages || [];
    const root = this.shadowRoot;
    const oldHistory = root.querySelector(".messages");
    const oldScrollTop = oldHistory?.scrollTop || 0;
    const keepScrolledToBottom =
      !oldHistory ||
      oldHistory.scrollHeight - oldHistory.scrollTop - oldHistory.clientHeight < 24;
    root.replaceChildren();

    const style = document.createElement("style");
    style.textContent = `
      :host{display:block}
      .card{padding:16px;background:var(--ha-card-background,var(--card-background-color,#fff));color:var(--primary-text-color);border-radius:var(--ha-card-border-radius,12px);box-shadow:var(--ha-card-box-shadow,none)}
      .messages{display:flex;flex-direction:column;gap:8px;max-height:420px;overflow:auto}
      .empty,.meta,.hint,.status{color:var(--secondary-text-color);font-size:.85em}
      .bubble{max-width:85%;padding:9px 12px;border-radius:14px;background:var(--secondary-background-color);overflow-wrap:anywhere}
      .outgoing{align-self:flex-end;background:var(--primary-color);color:var(--text-primary-color,#fff)}
      .incoming{align-self:flex-start}
      .meta{margin-top:4px}
      .compose{display:flex;gap:8px;margin-top:12px}
      textarea{flex:1;min-width:0;resize:vertical;font:inherit;color:var(--primary-text-color);background:var(--input-fill-color,transparent);border:1px solid var(--divider-color);border-radius:8px;padding:8px}
      button{font:inherit;color:var(--primary-text-color);background:var(--secondary-background-color);border:1px solid var(--divider-color);border-radius:8px;padding:8px 10px;cursor:pointer}
      button:disabled{opacity:.5;cursor:not-allowed}
      .emoji{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
      .emoji button{font-size:1.2em}
      audio{display:block;max-width:100%;margin-top:6px}
      .voice{margin-top:8px}
      .status{min-height:1.3em;margin-top:8px}
    `;
    root.append(style);

    const card = document.createElement("section");
    card.className = "card";
    const history = document.createElement("div");
    history.className = "messages";
    if (!this._entities?.messageSensor && !this._registryLoaded) {
      const loading = document.createElement("div");
      loading.className = "empty";
      loading.textContent = this._t("loading");
      history.append(loading);
    } else if (this._registryError) {
      const error = document.createElement("div");
      error.className = "empty";
      error.textContent = this._t("registryError");
      history.append(error);
    } else if (!this._entities?.messageSensor) {
      const unavailable = document.createElement("div");
      unavailable.className = "empty";
      unavailable.textContent = this._t("noChat");
      history.append(unavailable);
    } else if (!Array.isArray(messages) || messages.length === 0) {
      const empty = document.createElement("div");
      empty.className = "empty";
      empty.textContent = this._t("empty");
      history.append(empty);
    } else {
      for (const message of messages) {
        history.append(this._renderMessage(message));
      }
    }
    card.append(history);

    const form = document.createElement("form");
    form.className = "compose";
    const input = document.createElement("textarea");
    input.rows = 2;
    input.maxLength = Math.min(255, textEntity?.attributes?.max || 255);
    input.disabled = !this._entities?.textEntity || Boolean(this._registryError);
    input.placeholder = this._t("input");
    input.value = this._draft;
    input.addEventListener("input", () => {
      this._draft = input.value;
    });
    const send = document.createElement("button");
    send.type = "submit";
    send.textContent = this._t("send");
    send.disabled = input.disabled;
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      this._sendText(input.value);
    });
    form.append(input, send);
    card.append(form);

    const emojiBar = document.createElement("div");
    emojiBar.className = "emoji";
    emojiBar.setAttribute("aria-label", this._t("emoji"));
    for (const [code, emoji] of EMOJIS) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = emoji;
      button.title = `${this._t("emoji")} (${code})`;
      button.setAttribute("aria-label", `${this._t("emoji")} (${code})`);
      button.addEventListener("click", () => this._sendEmoji(code));
      emojiBar.append(button);
    }
    card.append(emojiBar);

    const voice = document.createElement("button");
    voice.className = "voice";
    voice.type = "button";
    voice.textContent = this._recorder ? this._t("stop") : this._t("microphone");
    voice.disabled = !this._recorder && !this._canRecord();
    voice.addEventListener("click", () => this._toggleRecording());
    card.append(voice);

    const hint = document.createElement("div");
    hint.className = "hint";
    hint.textContent = this._voiceHint();
    card.append(hint);

    const status = document.createElement("div");
    status.className = "status";
    status.setAttribute("role", "status");
    status.textContent = statusText(this);
    card.append(status);
    root.append(card);

    history.scrollTop = keepScrolledToBottom ? history.scrollHeight : oldScrollTop;
  }

  _renderMessage(message) {
    const bubble = document.createElement("article");
    bubble.className = `bubble ${message.is_from_watch ? "incoming" : "outgoing"}`;
    const content = document.createElement("div");
    const emoji = EMOJIS.find(([code]) => code === message.message);
    if (message.message_type === "emoji" && emoji) {
      content.textContent = emoji[1];
    } else if (message.message_type === "voice") {
      content.textContent = this._t("voiceMessage");
      if (message.audio_url) {
        const player = document.createElement("audio");
        player.controls = true;
        player.preload = "none";
        player.src = message.audio_url;
        player.addEventListener("error", () => {
          this._setStatus("audioFailed");
        });
        content.append(player);
      }
    } else {
      content.textContent = message.message || message.message_type || "";
    }
    bubble.append(content);

    const meta = document.createElement("div");
    meta.className = "meta";
    const sender = message.is_from_watch ? this._t("watch") : this._t("homeAssistant");
    const date = message.timestamp ? new Date(message.timestamp) : null;
    meta.textContent = date && !Number.isNaN(date.getTime())
      ? `${sender} · ${date.toLocaleString()}`
      : sender;
    bubble.append(meta);
    return bubble;
  }

  async _sendText(value) {
    const message = value.trim();
    if (!message) return;
    try {
      await this._hass.callService("text", "set_value", {
        entity_id: this._entities?.textEntity,
        value: message,
      });
      this._draft = "";
      const input = this.shadowRoot.querySelector("textarea");
      if (input) input.value = "";
      this._setStatus("");
    } catch (error) {
      console.error("Could not send Anio message:", error);
      this._setStatus("sendFailed", error);
    }
  }

  async _sendEmoji(code) {
    try {
      await this._hass.callService("anio", "send_emoji", {
        device_id: this._config.device_id,
        emoji_code: code,
      });
      this._setStatus("");
    } catch (error) {
      console.error("Could not send Anio emoji:", error);
      this._setStatus("emojiFailed", error);
    }
  }

  _canRecord() {
    return (
      Boolean(this._voiceDeviceId()) &&
      window.isSecureContext === true &&
      Boolean(navigator.mediaDevices?.getUserMedia) &&
      typeof window.MediaRecorder === "function"
    );
  }

  _voiceHint() {
    if (!this._voiceDeviceId()) return this._t("missingDevice");
    if (window.isSecureContext !== true) return this._t("secure");
    if (!navigator.mediaDevices?.getUserMedia || typeof window.MediaRecorder !== "function") {
      return this._t("unsupported");
    }
    return this._t("recordingPending");
  }

  async _toggleRecording() {
    if (this._recorder) {
      this._recorder.stop();
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const chunks = [];
      const recorder = new MediaRecorder(stream);
      this._recorder = recorder;
      recorder.addEventListener("dataavailable", (event) => {
        if (event.data.size) chunks.push(event.data);
      });
      recorder.addEventListener("error", (error) => {
        console.error("Could not record Anio voice message:", error);
        this._setStatus("recordFailed");
      });
      recorder.addEventListener("stop", async () => {
        clearTimeout(this._recordingTimeout);
        stream.getTracks().forEach((track) => track.stop());
        this._recorder = null;
        if (this._discardRecording) {
          this._discardRecording = false;
          return;
        }
        this._render();
        const blob = new Blob(chunks, {
          type: recorder.mimeType || chunks[0]?.type || "application/octet-stream",
        });
        await this._uploadVoice(blob);
      });
      recorder.start();
      this._render();
      this._recordingTimeout = setTimeout(() => {
        if (this._recorder) {
          this._setStatus("recordingTooLong");
          this._recorder.stop();
        }
      }, 30000);
    } catch (error) {
      console.error("Could not start Anio voice recording:", error);
      this._setStatus("recordFailed");
    }
  }

  async _uploadVoice(blob) {
    const url = `/api/anio/voice/${encodeURIComponent(this._voiceDeviceId())}/send`;
    try {
      const response = await fetch(url, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": blob.type || "application/octet-stream" },
        body: blob,
      });
      const result = await response.json();
      const errorKey = VOICE_ERROR_STRINGS[result?.code];
      this._setStatus(response.ok ? "voiceNotReady" : errorKey || "voiceNotReady");
    } catch (error) {
      console.error("Could not upload Anio voice message:", error);
      this._setStatus("voiceNotReady");
    }
  }

  _voiceDeviceId() {
    return this._config?.voice_device_id || this._entities?.anioDeviceId;
  }

  _setStatus(key, error = null) {
    setCardStatus(this, key, error);
  }
}

class AnioActivityCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._revision = 0;
    this._activityVisible = false;
    this._refreshInProgress = false;
    this._refreshFailed = false;
    this._visibilityChangeHandler = () => {
      if (document.visibilityState === "visible" && this._activityVisible) {
        this._refreshActivities(false);
      }
    };
  }

  connectedCallback() {
    document.addEventListener("visibilitychange", this._visibilityChangeHandler);
    if (typeof IntersectionObserver === "function") {
      this._visibilityObserver = new IntersectionObserver((entries) => {
        const visible = entries.some((entry) => entry.isIntersecting);
        if (visible && !this._activityVisible && document.visibilityState === "visible") {
          this._refreshActivities(false);
        }
        this._activityVisible = visible;
      });
      this._visibilityObserver.observe(this);
    } else {
      this._activityVisible = true;
      if (document.visibilityState === "visible") this._refreshActivities(false);
    }
  }

  disconnectedCallback() {
    this._visibilityObserver?.disconnect();
    this._visibilityObserver = null;
    this._activityVisible = false;
    document.removeEventListener("visibilitychange", this._visibilityChangeHandler);
  }

  setConfig(config) {
    if (!config?.device_id) {
      throw new Error("anio-activity-card requires an Anio device.");
    }
    this._revision++;
    this._config = config;
    this._entities = null;
    this._registryError = false;
    this._resolving = false;
    this._refreshInProgress = false;
    this._refreshFailed = false;
    this._signature = "";
    this._resolveDevice();
    this._render();
    if (this._activityVisible && document.visibilityState === "visible") {
      this._refreshActivities(false);
    }
  }

  set hass(hass) {
    const firstHass = !this._hass;
    this._hass = hass;
    if (!this._config) return;
    this._resolveDevice();
    if (firstHass && this._activityVisible && document.visibilityState === "visible") {
      this._refreshActivities(false);
    }
    const sensor = hass.states?.[this._entities?.activitySensor];
    const signature = JSON.stringify([
      hass.locale?.language, hass.config?.time_zone, sensor?.state,
      sensor?.attributes?.update_available, sensor?.attributes?.activities,
    ]);
    if (signature !== this._signature) {
      this._signature = signature;
      this._render();
    }
  }

  static getConfigElement() {
    return document.createElement("anio-device-card-editor");
  }

  static getStubConfig() {
    return { device_id: "" };
  }

  getCardSize() {
    return 4;
  }

  async _refreshActivities(force) {
    if (!this._hass || !this._config?.device_id || this._refreshInProgress) return;
    const revision = this._revision;
    this._refreshInProgress = true;
    this._refreshFailed = false;
    this._render();
    try {
      await this._hass.callService("anio", "refresh_activities", {
        device_id: this._config.device_id,
        force,
      });
    } catch (error) {
      console.error("Could not refresh Anio activities:", error);
      if (revision === this._revision) this._refreshFailed = true;
    } finally {
      if (revision === this._revision) {
        this._refreshInProgress = false;
        this._render();
      }
    }
  }

  _resolveDevice() {
    if (!this._hass || !this._config?.device_id || this._entities || this._resolving || this._registryError) return;
    const revision = this._revision;
    this._resolving = true;
    resolveAnioDevice(this._hass, this._config.device_id)
      .then((entities) => {
        if (revision !== this._revision) return;
        this._entities = entities;
      })
      .catch((error) => {
        if (revision !== this._revision) return;
        console.error("Could not resolve the Anio device:", error);
        this._registryError = true;
      })
      .finally(() => {
        if (revision !== this._revision) return;
        this._resolving = false;
        this._render();
      });
  }

  _render() {
    if (!this._config) return;
    const t = (key) => translate(this._hass, key);
    const sensor = this._hass?.states?.[this._entities?.activitySensor];
    const previousScroll = this.shadowRoot.querySelector(".activities")?.scrollTop || 0;
    this.shadowRoot.replaceChildren();
    const style = document.createElement("style");
    style.textContent = `
      :host{display:block}
      .card{padding:16px;background:var(--ha-card-background,var(--card-background-color,#fff));color:var(--primary-text-color);border-radius:var(--ha-card-border-radius,12px);box-shadow:var(--ha-card-box-shadow,none)}
      .header{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:12px}
      h2{font-size:1.2em;margin:0}
      button{font:inherit;color:var(--primary-text-color);background:var(--secondary-background-color);border:1px solid var(--divider-color);border-radius:8px;padding:8px 10px;cursor:pointer}
      button:disabled{opacity:.5;cursor:not-allowed}
      .activities{max-height:420px;overflow:auto}
      .activity{display:flex;gap:8px;padding:8px 0;border-bottom:1px solid var(--divider-color)}
      .body{flex:1;min-width:0;overflow-wrap:anywhere}
      .time,.meta,.empty{color:var(--secondary-text-color);font-size:.85em}
      .time{white-space:nowrap}
    `;
    this.shadowRoot.append(style);
    const card = document.createElement("section");
    card.className = "card";
    const heading = document.createElement("h2");
    heading.textContent = t("activitiesHeading");
    const header = document.createElement("div");
    header.className = "header";
    const refresh = document.createElement("button");
    refresh.className = "refresh";
    refresh.textContent = t(this._refreshInProgress ? "refreshingActivities" : "refreshActivities");
    refresh.disabled = !this._hass || this._refreshInProgress;
    refresh.addEventListener("click", () => this._refreshActivities(true));
    header.append(heading, refresh);
    card.append(header);
    const history = document.createElement("div");
    history.className = "activities";
    const notice = (text) => {
      const element = document.createElement("div");
      element.className = "empty";
      element.textContent = text;
      history.append(element);
    };
    if (this._registryError) notice(t("registryError"));
    else if (!this._entities) notice(t("loading"));
    else if (!this._entities.activitySensor || !sensor) notice(t("noActivitySensor"));
    else {
      if (this._refreshFailed || sensor.state === "unavailable" || sensor.attributes?.update_available === false) {
        notice(t("activityUnavailable"));
      }
      const activities = sensor.attributes?.activities;
      if (Array.isArray(activities) && activities.length) {
        for (const activity of activities) {
          const row = document.createElement("div");
          row.className = "activity";
          const icon = document.createElement("span");
          const body = document.createElement("div");
          body.className = "body";
          const title = document.createElement("div");
          const isZone = activity.type === "GEOFENCE_ENTERED" || activity.type === "GEOFENCE_LEFT";
          if (isZone) {
            icon.textContent = activity.type === "GEOFENCE_ENTERED" ? "🟢" : "🔴";
            title.textContent = t(activity.type === "GEOFENCE_ENTERED" ? "enteredZone" : "leftZone")
              .replace("{zone}", activity.zone || t("unknownZone"));
          } else {
            icon.textContent = activity.type === "LOW_BATTERY" ? "🔋" : "📌";
            title.textContent = activity.type === "LOW_BATTERY" ? t("lowBattery") : (activity.text || activity.type);
          }
          body.append(title);
          if (isZone) {
            const meta = document.createElement("div");
            meta.className = "meta";
            meta.textContent = t("anioZone");
            if (activity.type === "GEOFENCE_LEFT") {
              meta.textContent += ` · ${t("estimatedTime")}`;
              meta.title = t("estimatedDeparture");
            }
            body.append(meta);
          }
          const time = document.createElement("time");
          time.className = "time";
          const date = new Date(activity.display_timestamp);
          if (!Number.isNaN(date.getTime())) {
            time.dateTime = activity.display_timestamp;
            time.textContent = date.toLocaleString(this._hass?.locale?.language || "en", {
              dateStyle: "short", timeStyle: "short",
              ...(this._hass?.config?.time_zone ? { timeZone: this._hass.config.time_zone } : {}),
            });
          }
          row.append(icon, body, time);
          history.append(row);
        }
      } else if (!this._refreshFailed && sensor.state !== "unavailable" && sensor.attributes?.update_available !== false) {
        notice(t("noActivities"));
      }
    }
    card.append(history);
    this.shadowRoot.append(card);
    history.scrollTop = previousScroll;
  }
}

class AnioLocationCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._revision = 0;
    this._children = [];
  }

  setConfig(config) {
    if (!config?.device_id) {
      throw new Error("anio-location-card requires an Anio device.");
    }
    this._revision++;
    this._config = config;
    this._entities = null;
    this._helpers = null;
    this._loading = false;
    this._loadError = "";
    this._render();
    this._load();
  }

  set hass(hass) {
    this._hass = hass;
    this._load();
    this._syncHass();
  }

  static getConfigElement() {
    return document.createElement("anio-device-card-editor");
  }

  static getStubConfig() {
    return { device_id: "" };
  }

  _load() {
    if (
      !this._hass ||
      !this._config ||
      this._loading ||
      this._entities ||
      this._loadError
    ) {
      return;
    }
    this._loading = true;
    const revision = this._revision;
    Promise.all([
      resolveAnioDevice(this._hass, this._config.device_id),
      Promise.resolve().then(() => window.loadCardHelpers()),
    ])
      .then(([entities, helpers]) => {
        if (revision !== this._revision) return;
        this._entities = entities;
        this._helpers = helpers;
        this._render();
      })
      .catch((error) => {
        if (revision !== this._revision) return;
        console.error("Could not load the Anio location card:", error);
        this._entities = null;
        this._loadError = "locationCardError";
        this._render();
      });
  }

  getCardSize() {
    return 12;
  }

  _render() {
    if (!this._config) return;
    const root = this.shadowRoot;
    root.replaceChildren();
    this._children = [];
    this._localizedChildren = [];
    this._localizedLanguage = this._language();
    this._labels = {};

    const style = document.createElement("style");
    style.textContent = `
      :host{display:block}
      .content{display:flex;flex-direction:column;gap:8px}
      h2{font-size:1.2em;margin:8px 0 0;color:var(--primary-text-color)}
      .badges{display:flex;flex-wrap:wrap;gap:8px}
      .grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));grid-auto-rows:minmax(56px,auto);gap:8px}
      .large{grid-row:span 2}
      .large>*,.large{height:100%}
      .grid>*{min-width:0}
      .disabled{opacity:.5}
      .hint{color:var(--secondary-text-color);font-size:.85em}
    `;
    root.append(style);

    const content = document.createElement("div");
    content.className = "content";
    root.append(content);
    if (!this._entities || !this._helpers) {
      this._labels.state = document.createElement("div");
      this._labels.state.className = "hint";
      this._labels.state.setAttribute("role", "status");
      content.append(this._labels.state);
      this._syncHass();
      return;
    }

    const entities = this._entities;
    this._missing = [
      "signalStrength", "positionSource", "gpsAccuracy", "battery", "location",
      "locationRequest", "locationRequestStatus", "lastResponse", "explorer",
      "lastLocation", "radarMode", "findMyDevice", "bellProtection",
    ].filter((key) => !entities[key]);

    const badges = document.createElement("div");
    badges.className = "badges";
    for (const entity of [
      entities.signalStrength, entities.positionSource, entities.gpsAccuracy, entities.battery,
    ]) {
      if (entity) this._appendNative(badges, "badge", {
        type: "entity", entity, show_name: false, show_state: true, show_icon: true,
      });
    }
    content.append(badges);

    this._labels.location = document.createElement("h2");
    content.append(this._labels.location);
    if (entities.location) this._appendNative(content, "card", {
      type: "map",
      entities: [{ entity: entities.location, color: "indigo", label_mode: "icon" }],
      theme_mode: "auto",
    });

    const grid = document.createElement("div");
    grid.className = "grid";
    if (entities.locationRequest) {
      const wrapper = document.createElement("div");
      wrapper.className = "large";
      this._appendNative(wrapper, "card", {
        type: "button",
        entity: entities.locationRequest,
        show_name: true,
        show_icon: true,
        tap_action: this._pressAction(entities.locationRequest),
      }, "requestLocation");
      grid.append(wrapper);
    }
    for (const [entity, nameKey] of [
      [entities.location, null],
      [entities.locationRequestStatus, "locationRequestStatus"],
      [entities.lastResponse, "lastResponse"],
      [entities.explorer, "explorer"],
      [entities.lastLocation, "lastLocation"],
      [entities.radarMode, "radarMode"],
    ]) {
      if (entity) this._appendNative(grid, "card", {
        type: "tile", entity, ...(nameKey ? {} : { name: "" }), vertical: false,
      }, nameKey);
    }
    content.append(grid);

    this._labels.functions = document.createElement("h2");
    content.append(this._labels.functions);
    const functions = document.createElement("div");
    functions.className = "grid";
    if (entities.findMyDevice) {
      this._ringWrapper = document.createElement("div");
      this._appendNative(this._ringWrapper, "card", {
        type: "tile",
        entity: entities.findMyDevice,
        hide_state: true,
        vertical: true,
        tap_action: this._pressAction(entities.findMyDevice),
        icon_tap_action: this._pressAction(entities.findMyDevice),
      }, "ringWatch");
      functions.append(this._ringWrapper);
    } else {
      this._ringWrapper = null;
    }
    if (entities.bellProtection) this._appendNative(functions, "card", {
      type: "tile",
      entity: entities.bellProtection,
      icon: "mdi:shield-lock",
      vertical: true,
      features: [{ type: "toggle" }],
      features_position: "bottom",
    }, "bellProtection");
    content.append(functions);
    this._labels.protection = document.createElement("div");
    this._labels.protection.className = "hint";
    content.append(this._labels.protection);
    this._labels.missing = document.createElement("div");
    this._labels.missing.className = "hint";
    this._labels.missing.setAttribute("role", "status");
    content.append(this._labels.missing);
    this._syncHass();
  }

  _appendNative(parent, kind, config, nameKey = null) {
    if (nameKey) config = { ...config, name: translate(this._hass, nameKey) };
    const element = kind === "badge"
      ? this._helpers.createBadgeElement(config)
      : this._helpers.createCardElement(config);
    element.hass = this._hass;
    this._children.push(element);
    if (nameKey) this._localizedChildren.push({ element, config, nameKey });
    parent.append(element);
  }

  _language() {
    return this._hass?.locale?.language?.toLowerCase().startsWith("de") ? "de" : "en";
  }

  _pressAction(entity) {
    return {
      action: "perform-action",
      perform_action: "button.press",
      target: { entity_id: entity },
    };
  }

  _syncHass() {
    if (!this._labels) return;
    for (const child of this._children) child.hass = this._hass;
    const language = this._language();
    if (this._localizedLanguage !== language) {
      this._localizedLanguage = language;
      for (const { element, config, nameKey } of this._localizedChildren) {
        element.setConfig({ ...config, name: translate(this._hass, nameKey) });
      }
    }
    if (this._labels.state) {
      this._labels.state.textContent = translate(this._hass, this._loadError || "loading");
      return;
    }
    this._labels.location.textContent = translate(this._hass, "locationHeading");
    this._labels.functions.textContent = translate(this._hass, "functionsHeading");
    const keys = {
      signalStrength: "networkQuality",
      locationRequest: "requestLocation",
      findMyDevice: "ringWatch",
    };
    this._labels.missing.textContent = this._missing.length
      ? `${translate(this._hass, "missingEntities")}: ${this._missing.map((key) =>
        translate(this._hass, keys[key] || key)).join(", ")}`
      : "";
    const protection = this._hass?.states?.[this._entities.bellProtection]?.state;
    const disabled = protection !== "off";
    if (this._ringWrapper) {
      this._ringWrapper.inert = disabled;
      this._ringWrapper.classList.toggle("disabled", disabled);
      this._ringWrapper.setAttribute("aria-disabled", String(disabled));
    }
    this._labels.protection.textContent = protection === "on"
      ? translate(this._hass, "bellProtectionOn")
      : disabled ? translate(this._hass, "bellProtectionUnavailable") : "";
  }
}

if (!customElements.get("anio-location-card")) {
  customElements.define("anio-location-card", AnioLocationCard);
}

if (!customElements.get("anio-chat-card")) {
  customElements.define("anio-chat-card", AnioChatCard);
}

if (!customElements.get("anio-activity-card")) {
  customElements.define("anio-activity-card", AnioActivityCard);
}

window.customCards = window.customCards || [];
const cardLanguage = (document.documentElement.lang || "en").split("-")[0];
const cardMetadata = {
  de: [
    {
      name: "Anio-Chat",
      description: "Chat mit einer Anio-Uhr: Text, Emojis und Sprachvorbereitung.",
    },
    {
      name: "Anio-Standort",
      description: "Standort anzeigen, Aktualisierung anfordern und Uhr klingeln lassen.",
    },
    {
      name: "Anio-Aktivitäten",
      description: "Gespeicherte Aktivitäten und Anio-Zonenwechsel anzeigen.",
    },
  ],
  en: [
    {
      name: "Anio Chat",
      description: "Chat with an Anio watch using text, emojis, and voice preparation.",
    },
    {
      name: "Anio Location",
      description: "Show the watch location, request an update, and ring the watch.",
    },
    {
      name: "Anio Activities",
      description: "Show stored activities and Anio zone transitions.",
    },
  ],
}[cardLanguage] || [
  {
    name: "Anio Chat",
    description: "Chat with an Anio watch using text, emojis, and voice preparation.",
  },
  {
    name: "Anio Location",
    description: "Show the watch location, request an update, and ring the watch.",
  },
  {
    name: "Anio Activities",
    description: "Show stored activities and Anio zone transitions.",
  },
];
window.customCards.push(
  { type: "anio-chat-card", ...cardMetadata[0] },
  { type: "anio-location-card", ...cardMetadata[1] },
  { type: "anio-activity-card", ...cardMetadata[2] },
);
