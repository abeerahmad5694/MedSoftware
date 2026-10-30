/* Separate opt-in Urdu suggestion workflow. Inventory writes remain in the editor. */
(() => {
  "use strict";
  const $ = (name) => document.getElementById("iu-urdu-" + name);
  const panel = document.getElementById("iu-urdu");
  if (!panel || !window.InventoryEditorUrdu || !window.UrduDictionary) return;
  const config = JSON.parse(document.getElementById("iu-config").textContent);
  const engine = window.UrduDictionary;
  const glossary = { ...engine.DEFAULT_GLOSSARY, ...config.urduGlossary };
  const dictionary = new engine.Dictionary(config.storageKey);
  const ready = dictionary.load().then(() => {
    $("cache-status").textContent =
      dictionary.warning ||
      `${dictionary.entries.size} saved words in this browser. No database needed for loaded names.`;
  });
  let running = false,
    controller = null,
    stopped = false,
    candidates = [];
  function node(tag, text) {
    const el = document.createElement(tag);
    if (text !== undefined) el.textContent = text;
    return el;
  }
  function status(text, error = false) {
    $("status").textContent = text;
    $("status").classList.toggle("iu-urdu-error", error);
  }
  function network() {
    const offline = navigator.onLine === false;
    $("network").textContent = offline
      ? "Offline — connect to generate"
      : "Online • browser-to-Google • database-independent";
    $("generate").disabled = offline || running;
    $("stop").disabled = !running;
    $("import").disabled = running;
    $("export").disabled = running;
    $("apply").disabled = running || !candidates.some((c) => c.check?.checked);
    if (offline && running) {
      stopped = true;
      controller?.abort();
    }
  }
  function addResult(snapshot, result) {
    const card = node("section"),
      title = node("label"),
      check = node("input");
    card.className = "iu-urdu-result";
    check.type = "checkbox";
    check.checked = !!result.suggestion;
    check.disabled = !result.suggestion;
    title.append(check, node("strong", `#${snapshot.id} · ${snapshot.source}`));
    check.addEventListener("change", network);
    card.append(title);
    if (snapshot.originalUrdu) {
      const old = node("p", "Current: " + snapshot.originalUrdu);
      old.dir = "auto";
      card.append(old);
    }
    if (result.suggestion) {
      const label = node("label", "Urdu suggestion — edit before applying");
      const input = node("textarea");
      input.value = result.suggestion;
      input.maxLength = 500;
      input.dir = "rtl";
      input.lang = "ur";
      input.rows = 2;
      input.setAttribute(
        "aria-label",
        `Urdu suggestion for ${snapshot.source}`,
      );
      label.append(input);
      card.append(label);
      candidates.push({ ...snapshot, check, input });
    } else {
      const error = node(
        "p",
        result.error || "No suggestion. Try again later.",
      );
      error.className = "iu-urdu-error";
      card.append(error);
    }
    $("results").append(card);
  }
  async function generate() {
    if (running || navigator.onLine === false) return;
    let snapshots;
    try {
      snapshots = window.InventoryEditorUrdu.snapshot().filter(
        (row) => $("overwrite").checked || !row.originalUrdu.trim(),
      );
      if (!snapshots.length)
        throw Error(
          "No eligible items. Select items or choose all visible items in Action scope; existing Urdu names are skipped by default.",
        );
      if (
        candidates.length &&
        !confirm(
          "Replace the current suggestion preview? Unapplied suggestions will be lost.",
        )
      )
        return;
    } catch (error) {
      status(error.message, true);
      return;
    }
    running = true;
    stopped = false;
    candidates = [];
    $("results").replaceChildren();
    $("progress").hidden = false;
    $("progress").max = snapshots.length;
    $("progress").value = 0;
    network();
    controller = new AbortController();
    try {
      await ready;
      const outcome = await engine.generate(
        snapshots.map((row) => row.source),
        {
          dictionary,
          glossary,
          signal: controller.signal,
          onProgress(stats) {
            $("progress").max = Math.max(1, stats.unique);
            $("progress").value = stats.local + stats.resolved;
            status(
              `${stats.unique} unique words · ${stats.local} local/cached · ${stats.resolved} newly fetched · ${stats.requests} API requests`,
            );
          },
        },
      );
      outcome.results.forEach((result, index) =>
        addResult(snapshots[index], result),
      );
      const stats = outcome.stats;
      const failures = outcome.results.filter(
        (result) => !result.suggestion,
      ).length;
      $("cache-status").textContent =
        outcome.warning ||
        `${dictionary.entries.size} saved words. Future runs request missing words only.`;
      status(
        `${stats.stopped ? "Stopped. " : ""}${candidates.length} suggestions · ${failures} unavailable · ${stats.unique} unique words · ${stats.requests} API requests. ${stats.error || "Review spellings before applying. Nothing saved to inventory."}`,
        !!stats.error,
      );
    } catch (error) {
      status(
        stopped
          ? "Stopped. Completed words remain cached for the next run."
          : error.message,
        !stopped,
      );
    } finally {
      running = false;
      controller = null;
      network();
    }
  }
  $("export").onclick = async () => {
    if (running) return;
    try {
      await ready;
      const url = URL.createObjectURL(
        new Blob([dictionary.exportJSON(glossary)], {
          type: "application/json;charset=utf-8",
        }),
      );
      const link = node("a");
      link.href = url;
      link.download = "urdu_cache.json";
      document.body.append(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      status(
        "Dictionary exported. Edit word spellings in the JSON file and import it to keep corrections for future runs.",
      );
    } catch {
      status(
        "Your browser could not export the dictionary. Try another supported browser; inventory is unchanged.",
        true,
      );
    }
  };
  $("import").onclick = () => $("file").click();
  $("file").onchange = async () => {
    const file = $("file").files[0];
    if (!file || running) return;
    running = true;
    network();
    try {
      if (file.size > 1024 * 1024)
        throw Error("Dictionary file must be at most 1 MB.");
      if (
        !confirm(
          "Import reviewed word spellings? Imported entries override existing spellings for those words. Inventory names are not changed.",
        )
      )
        return;
      await ready;
      const total = await dictionary.importJSON(await file.text());
      $("cache-status").textContent =
        dictionary.warning ||
        `${dictionary.entries.size} saved words in this browser.`;
      status(
        `Imported ${total} reviewed word spellings. Generate again to use them. No inventory changes.`,
      );
    } catch (error) {
      status(error.message, true);
    } finally {
      $("file").value = "";
      running = false;
      network();
    }
  };
  $("generate").onclick = generate;
  $("stop").onclick = () => {
    stopped = true;
    controller?.abort();
  };
  $("apply").onclick = () => {
    if (running) return;
    try {
      const chosen = candidates.filter((c) => c.check.checked);
      if (!chosen.length) return;
      const result = window.InventoryEditorUrdu.apply(
        chosen.map((c) => ({ ...c, text: c.input.value })),
      );
      status(
        `${result.applied} suggestions applied to drafts. ${result.skipped} skipped because the item changed since generation. Review & save to persist.`,
      );
      chosen.forEach((c) => {
        c.check.checked = false;
        c.check.disabled = true;
        c.input.disabled = true;
      });
      network();
    } catch (error) {
      status(error.message, true);
    }
  };
  window.addEventListener("online", network);
  window.addEventListener("offline", network);
  network();
})();