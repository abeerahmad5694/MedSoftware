/* Restricted arithmetic parser. No eval, Function, property access or executable JS. */
(function (root) {
  "use strict";
  const derived = {
    discounted_base_price: ["base_price", "base_disc_per"],
    discounted_ws_price: ["ws_price", "ws_disc_per"],
  };
  function parse(text, allowed) {
    if (typeof text !== "string" || text.length > 300)
      throw Error("Formula must be 1–300 characters.");
    const tokens =
      text.match(/\d+(?:\.\d+)?|[A-Za-z_][A-Za-z_0-9]*|[()+\-*/]|\S/g) || [];
    let pos = 0;
    const refs = new Set();
    function atom() {
      const token = tokens[pos++];
      if (token === "+" || token === "-")
        return { op: "unary" + token, a: atom() };
      if (token === "(") {
        const node = expression();
        if (tokens[pos++] !== ")") throw Error("Missing closing parenthesis.");
        return node;
      }
      if (/^\d+(?:\.\d+)?$/.test(token || "")) return { number: Number(token) };
      if (allowed.includes(token)) {
        refs.add(token);
        return { field: token };
      }
      throw Error(
        "Unknown field or invalid token: " + (token || "end of formula"),
      );
    }
    function product() {
      let node = atom();
      while (["*", "/"].includes(tokens[pos]))
        node = { op: tokens[pos++], a: node, b: atom() };
      return node;
    }
    function expression() {
      let node = product();
      while (["+", "-"].includes(tokens[pos]))
        node = { op: tokens[pos++], a: node, b: product() };
      return node;
    }
    const ast = expression();
    if (pos !== tokens.length) throw Error("Unexpected token: " + tokens[pos]);
    return { ast, refs: [...refs] };
  }
  function number(row, key) {
    if (derived[key]) {
      const [price, discount] = derived[key];
      return number(row, price) * (1 - number(row, discount) / 100);
    }
    const value = Number(row[key] || 0);
    if (!Number.isFinite(value)) throw Error("Invalid number in " + key);
    return value;
  }
  function evaluate(node, row) {
    if ("number" in node) return node.number;
    if (node.field) return number(row, node.field);
    const a = evaluate(node.a, row);
    if (node.op === "unary-") return -a;
    if (node.op === "unary+") return a;
    const b = evaluate(node.b, row);
    if (node.op === "/" && b === 0) throw Error("Division by zero.");
    return node.op === "+"
      ? a + b
      : node.op === "-"
        ? a - b
        : node.op === "*"
          ? a * b
          : a / b;
  }
  function compile(rules, fields) {
    if (!Array.isArray(rules) || rules.length > 30)
      throw Error("Use at most 30 rules.");
    const numeric = fields
      .filter((f) => f.type === "number")
      .map((f) => f.name);
    const byTarget = new Map();
    for (const rule of rules) {
      if (!numeric.includes(rule.target))
        throw Error("Choose a numeric destination.");
      if (byTarget.has(rule.target))
        throw Error("Only one formula per destination is allowed.");
      const parsed = parse(rule.expression, [
        ...numeric,
        ...Object.keys(derived),
      ]);
      byTarget.set(rule.target, {
        ...rule,
        ...parsed,
        dependencies: parsed.refs.flatMap((r) => derived[r] || [r]),
      });
    }
    const sorted = [],
      visiting = new Set(),
      visited = new Set();
    function visit(target) {
      if (visiting.has(target))
        throw Error("Circular formula involving " + target);
      if (visited.has(target)) return;
      visiting.add(target);
      const rule = byTarget.get(target);
      for (const dep of rule.dependencies) if (byTarget.has(dep)) visit(dep);
      visiting.delete(target);
      visited.add(target);
      sorted.push(rule);
    }
    for (const target of byTarget.keys()) visit(target);
    return sorted;
  }
  function run(row, compiled, fields, changed = null) {
    const result = { ...row },
      affected = changed === null ? null : new Set([changed]);
    for (const rule of compiled) {
      if (affected && !rule.dependencies.some((d) => affected.has(d))) continue;
      const value = evaluate(rule.ast, result);
      const field = fields.find((f) => f.name === rule.target);
      const rounded =
        field.step === "1"
          ? Math.round(value)
          : Math.round((value + Number.EPSILON) * 100) / 100;
      const limit = rule.target.endsWith("_disc_per")
        ? 100
        : field.step === "1"
          ? 2147483647
          : 9999999999.99;
      if (
        !Number.isFinite(value) ||
        value < 0 ||
        rounded > limit ||
        (["carton_qty", "dzn_qty"].includes(rule.target) && rounded < 1)
      ) {
        throw Error("Formula result outside allowed range for " + rule.target);
      }
      result[rule.target] =
        field.step === "1" ? String(rounded) : rounded.toFixed(2);
      if (affected) affected.add(rule.target);
    }
    return result;
  }
  const api = { parse, compile, run, number };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.InventoryFormulas = api;
})(typeof window !== "undefined" ? window : globalThis);