/* Browser-only transliteration/cache engine. No Django or database calls. */
(function (root) {
  "use strict";
  const DEFAULT_GLOSSARY = Object.freeze({
    LIGHT: "لائٹ",
    PANEL: "پینل",
    WAY: "وے",
    BULB: "بلب",
    OSAKA: "اوساکا",
    SWITCH: "سوئچ",
    SOCKET: "ساکٹ",
    WIRE: "وائر",
    CABLE: "کیبل",
    FAN: "فین",
    BOX: "باکس",
    GANG: "گینگ",
    DIMMER: "ڈمر",
    HOLDER: "ہولڈر",
  });
  const LETTERS = Object.fromEntries(
    [..."ABCDEFGHIJKLMNOPQRSTUVWXYZ"].map((letter, i) => [
      letter,
      [
        "اے",
        "بی",
        "سی",
        "ڈی",
        "ای",
        "ایف",
        "جی",
        "ایچ",
        "آئی",
        "جے",
        "کے",
        "ایل",
        "ایم",
        "این",
        "او",
        "پی",
        "کیو",
        "آر",
        "ایس",
        "ٹی",
        "یو",
        "وی",
        "ڈبلیو",
        "ایکس",
        "وائی",
        "زیڈ",
      ][i],
    ]),
  );
  const tokens = (text) => text.match(/[A-Za-z0-9]+/g) || [];
  const isUrdu = (value) =>
    typeof value === "string" &&
    /[\u0620-\u063f\u0641-\u064a\u066e-\u06d3\u06fa-\u06fc]/.test(value);
  const validText = (value) =>
    isUrdu(value) &&
    value.length <= 200 &&
    !/[<>\x00-\x1f\u202a-\u202e\u2066-\u2069]/.test(value);
  const validProviderText = (value) =>
    validText(value) && !/[A-Za-z0-9,،]/.test(value);
  function parts(token, glossary) {
    const match = /^(\d+)([A-Za-z]{2,})$/.exec(token);
    if (
      match &&
      (glossary[match[2].toUpperCase()] ||
        match[2].length > 3 ||
        /^(VM|SR)$/i.test(match[2]))
    )
      return [match[1] + "-", match[2]];
    return /^[A-Za-z]+$/.test(token) ? ["", token] : ["", null];
  }
  function lookup(word, entries, glossary) {
    const key = word.toUpperCase(),
      cached = entries.get(key);
    if (cached?.kind === "manual" && validText(cached.text)) return cached.text;
    if (glossary[key]) return glossary[key];
    if (word.length <= 3)
      return [...key].map((c) => LETTERS[c]).join(" ") + ` (${key})`;
    return cached && validProviderText(cached.text) ? cached.text : null;
  }
  function uniqueWords(names, entries, glossary) {
    const all = new Set(),
      missing = new Set();
    for (const name of names)
      for (const token of tokens(name)) {
        const [, word] = parts(token, glossary);
        if (word) {
          all.add(word.toUpperCase());
          if (!lookup(word, entries, glossary)) missing.add(word.toUpperCase());
        }
      }
    return { all: [...all], missing: [...missing].sort() };
  }
  function convert(name, entries, glossary) {
    const missing = new Set();
    const text = name
      .replace(/[A-Za-z0-9]+/g, (token) => {
        const [prefix, word] = parts(token, glossary);
        if (!word) return token;
        const value = lookup(word, entries, glossary);
        if (!value) {
          missing.add(word);
          return token;
        }
        return prefix + value;
      })
      .replace(/\s*\+\s*/g, " + ")
      .replace(/\s+/g, " ")
      .trim();
    const valid = !missing.size && isUrdu(text) && text.length <= 500;
    return {
      source: name,
      suggestion: valid ? text : null,
      error: missing.size
        ? `Missing words: ${[...missing].join(", ")}. Retry online or import reviewed spellings.`
        : valid
          ? ""
          : "No Urdu words, or result exceeds 500 characters.",
    };
  }
  // Never assume the endpoint returns one result per submitted word. It may
  // return a single phrase. Cache only exact echoed keys or an exact, complete
  // comma-delimited mapping; ambiguous/malformed output is discarded.
  function parseResponse(data, words) {
    const result = new Map(),
      expected = words.map((w) => w.toLowerCase());
    if (
      !Array.isArray(data) ||
      data[0] !== "SUCCESS" ||
      !Array.isArray(data[1])
    )
      return result;
    const rows = data[1];
    if (
      rows.length === 1 &&
      words.length > 1 &&
      typeof rows[0]?.[0] === "string" &&
      rows[0][0].toLowerCase() === expected.join(",")
    ) {
      const combined = rows[0]?.[1]?.[0];
      if (typeof combined !== "string") return result;
      const values = combined.split(/[,،]/).map((s) => s.trim());
      if (values.length === words.length && values.every(validProviderText))
        words.forEach((w, i) => result.set(w.toUpperCase(), values[i]));
      return result;
    }
    const seen = new Set();
    for (const row of rows) {
      if (
        !Array.isArray(row) ||
        typeof row[0] !== "string" ||
        !Array.isArray(row[1])
      )
        return new Map();
      const word = row[0].toLowerCase(),
        value = row[1][0];
      if (
        !expected.includes(word) ||
        seen.has(word) ||
        !validProviderText(value)
      )
        return new Map();
      seen.add(word);
      result.set(word.toUpperCase(), value.trim());
    }
    return result;
  }
  class Dictionary {
    constructor(scope, indexedDB) {
      this.scope = scope;
      this.entries = new Map();
      this.warning = "";
      this.storageUnavailable = false;
      try {
        this.indexedDB = indexedDB === undefined ? root.indexedDB : indexedDB;
      } catch {
        this.indexedDB = null;
      }
    }
    async open() {
      if (!this.indexedDB || this.storageUnavailable)
        throw Error("IndexedDB unavailable");
      return new Promise((resolve, reject) => {
        let finished = false;
        const timer = setTimeout(() => {
          finished = true;
          reject(Error("Dictionary storage timed out"));
        }, 3000);
        const request = this.indexedDB.open("erp-urdu-word-cache", 1);
        request.onupgradeneeded = () => {
          const store = request.result.createObjectStore("words", {
            keyPath: "key",
          });
          store.createIndex("scope", "scope");
        };
        request.onsuccess = () => {
          clearTimeout(timer);
          if (finished) request.result.close();
          else {
            finished = true;
            resolve(request.result);
          }
        };
        request.onerror = request.onblocked = () => {
          clearTimeout(timer);
          finished = true;
          reject(Error("Dictionary storage unavailable"));
        };
      });
    }
    async transaction(mode, operate) {
      const db = await this.open();
      try {
        return await new Promise((resolve, reject) => {
          const tx = db.transaction("words", mode);
          let request;
          const timer = setTimeout(() => {
            try {
              tx.abort();
            } catch {}
            reject(Error("Dictionary transaction timed out"));
          }, 5000);
          try {
            request = operate(tx.objectStore("words"));
          } catch (error) {
            clearTimeout(timer);
            tx.abort();
            reject(error);
            return;
          }
          tx.oncomplete = () => {
            clearTimeout(timer);
            resolve(request?.result);
          };
          tx.onerror = tx.onabort = () => {
            clearTimeout(timer);
            reject(tx.error || Error("Dictionary write failed"));
          };
        });
      } finally {
        db.close();
      }
    }
    async load() {
      try {
        const records = await this.transaction("readonly", (store) =>
          store.index("scope").getAll(this.scope),
        );
        for (const r of records)
          if (
            /^[A-Z]+$/.test(r.word) &&
            validText(r.text) &&
            ["provider", "manual"].includes(r.kind)
          )
            this.entries.set(r.word, { text: r.text, kind: r.kind });
      } catch {
        this.storageUnavailable = true;
        this.warning =
          "Browser storage unavailable. Using a temporary in-memory dictionary; export JSON to keep new spellings.";
      }
      return this;
    }
    async save(values, kind = "provider") {
      const records = [];
      for (const [word, text] of values) {
        const key = word.toUpperCase();
        if (
          !/^[A-Z]{1,255}$/.test(key) ||
          !(kind === "manual" ? validText(text) : validProviderText(text))
        )
          continue;
        if (kind === "provider" && this.entries.get(key)?.kind === "manual")
          continue;
        this.entries.set(key, { text, kind });
        records.push({
          key: `${this.scope}|${key}`,
          scope: this.scope,
          word: key,
          text,
          kind,
        });
      }
      if (!records.length) return;
      try {
        await this.transaction("readwrite", (store) => {
          records.forEach((r) => store.put(r));
        });
      } catch {
        this.storageUnavailable = true;
        this.warning =
          "Browser storage unavailable. New spellings remain in memory only; export JSON to retain them.";
      }
    }
    async importJSON(text) {
      if (text.length > 1024 * 1024)
        throw Error("Dictionary JSON must be at most 1 MB.");
      let value;
      try {
        value = JSON.parse(text);
      } catch {
        throw Error("Invalid JSON dictionary.");
      }
      if (!value || typeof value !== "object" || Array.isArray(value))
        throw Error(
          "Use a JSON object mapping English words to Urdu spellings.",
        );
      const entries = Object.entries(value);
      if (
        !entries.length ||
        entries.length > 5000 ||
        entries.some(([w, v]) => !/^[A-Za-z]{1,255}$/.test(w) || !validText(v))
      )
        throw Error(
          "Invalid dictionary. Use 1–5000 alphabetic word keys and Urdu values up to 200 characters.",
        );
      if (
        new Set(entries.map(([w]) => w.toUpperCase())).size !== entries.length
      )
        throw Error("Duplicate word keys with different capitalization.");
      await this.save(entries, "manual");
      return entries.length;
    }
    exportJSON(glossary) {
      const output = { ...glossary };
      for (const [word, value] of this.entries)
        if (value.kind === "manual" || !output[word]) output[word] = value.text;
      return JSON.stringify(output, null, 2);
    }
  }
  async function generate(names, options) {
    const {
      dictionary,
      signal,
      onProgress = () => {},
      isOnline = () => root.navigator?.onLine !== false,
      fetchFn = root.fetch.bind(root),
      timeoutMs = 10000,
      budgetMs = 90000,
    } = options;
    if (!isOnline())
      throw Error("Offline: connect before generating suggestions.");
    if (
      !Array.isArray(names) ||
      !names.length ||
      names.length > 1000 ||
      names.some((n) => typeof n !== "string" || !n.trim() || n.length > 255)
    )
      throw Error("Choose 1–1000 item names, each at most 255 characters.");
    const glossary = { ...DEFAULT_GLOSSARY, ...options.glossary };
    const { all, missing } = uniqueWords(names, dictionary.entries, glossary);
    const stats = {
      unique: all.length,
      local: all.length - missing.length,
      missing: missing.length,
      resolved: 0,
      requests: 0,
      stopped: false,
      error: "",
    };
    if (missing.length > 300)
      throw Error("More than 300 uncached words. Select fewer items per run.");
    const runController = new AbortController();
    const abort = () => runController.abort();
    signal?.addEventListener("abort", abort, { once: true });
    if (signal?.aborted) abort();
    const budget = setTimeout(() => {
      stats.error =
        "Time limit reached. Completed words are cached; generate again to resume.";
      abort();
    }, budgetMs);
    let fatal = false;
    const active = () => !runController.signal.aborted && !fatal && isOnline();
    const progress = () => onProgress({ ...stats });
    async function request(words) {
      if (!active()) return new Map();
      const controller = new AbortController(),
        cancel = () => controller.abort();
      runController.signal.addEventListener("abort", cancel, { once: true });
      const timer = setTimeout(cancel, timeoutMs);
      const params = new URLSearchParams({
        itc: "ur-t-i0-und",
        num: "1",
        cp: "0",
        cs: "1",
        ie: "utf-8",
        oe: "utf-8",
        app: "demopage",
        text: words.join(",").toLowerCase(),
      });
      stats.requests++;
      progress();
      try {
        const response = await fetchFn(
          `https://inputtools.google.com/request?${params}`,
          {
            signal: controller.signal,
            mode: "cors",
            credentials: "omit",
            redirect: "error",
            referrerPolicy: "no-referrer",
          },
        );
        if (!response.ok)
          throw Error(
            response.status === 429
              ? "Google rate limit reached. Wait before retrying."
              : `Google service unavailable (${response.status}).`,
          );
        let data;
        try {
          data = await response.json();
        } catch {
          throw Error(
            "Google returned an invalid response. Please retry later.",
          );
        }
        if (!active()) return new Map();
        return parseResponse(data, words);
      } catch (error) {
        if (!runController.signal.aborted) {
          fatal = true;
          stats.error =
            error.name === "AbortError"
              ? "Google request timed out. Retry to fetch only missing words."
              : error instanceof TypeError
                ? "Google could not be reached. Check internet access or browser cross-origin restrictions."
                : error.message;
        }
        return new Map();
      } finally {
        clearTimeout(timer);
        runController.signal.removeEventListener("abort", cancel);
      }
    }
    async function keep(values) {
      await dictionary.save(values);
      stats.resolved += values.size;
      progress();
    }
    try {
      progress();
      for (let offset = 0; offset < missing.length && active(); offset += 20) {
        const batch = missing.slice(offset, offset + 20);
        const mapped = await request(batch);
        await keep(mapped);
        const fallback =
          batch.length > 1 ? batch.filter((word) => !mapped.has(word)) : [];
        // A transport error stops the queue. Only ambiguous successful batch
        // responses fall back to individual words, with at most four in flight.
        let index = 0;
        await Promise.all(
          Array.from({ length: Math.min(4, fallback.length) }, async () => {
            while (index < fallback.length && active()) {
              const word = fallback[index++];
              const translated = await request([word]);
              await keep(translated);
            }
          }),
        );
      }
    } finally {
      clearTimeout(budget);
      signal?.removeEventListener("abort", abort);
    }
    stats.stopped = signal?.aborted || !isOnline();
    return {
      results: names.map((n) => convert(n, dictionary.entries, glossary)),
      stats,
      warning: dictionary.warning,
    };
  }
  const api = {
    Dictionary,
    DEFAULT_GLOSSARY,
    parts,
    lookup,
    uniqueWords,
    convert,
    parseResponse,
    generate,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.UrduDictionary = api;
})(typeof window !== "undefined" ? window : globalThis);