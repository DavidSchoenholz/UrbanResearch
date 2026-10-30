// Phase 2 pipeline page: diagram, design decisions, limitations, next steps, audits.
document.addEventListener("DOMContentLoaded", () => {
  const { D, el, renderList } = window.Site;
  const p = D.phase2;
  if (!p) return;

  document.getElementById("intro").innerHTML = p.intro;

  // Module purpose by file name, from the README's Layout table.
  const purpose = {};
  p.modules.rows.forEach(([mod, desc]) => { purpose[mod.replace(/<\/?code>/g, "")] = desc; });
  const mod = (name) => `<li><code>${name.replace("pipeline/", "")}</code>: ${purpose[name] || ""}</li>`;

  const stages = [
    { h: "Zoning", what: "What the rules allowed on the site on the day the application was filed.",
      mods: ["pipeline/zoning.py", "pipeline/spatial.py"] },
    { h: "Application", what: "A rezoning or other planning application is filed and decided.",
      mods: [], note: "Applications are a canonical table in <code>schema.py</code>; whether each needed a rezoning is carried by its <code>requires_rezoning</code> field." },
    { h: "Permit", what: "Building permits are issued and grouped into one project per development.",
      mods: ["pipeline/linking.py"] },
    { h: "Completion", what: "The project's permits are all cleared; results are compared with official counts.",
      mods: ["pipeline/survival.py", "pipeline/reconcile.py"],
      note: "<strong>Caution:</strong> in the code a project is complete when all its observed permits are cleared. Phase 1 found that <a href=\"toronto.html#limit-4\">cleared permits are not completions</a> in Toronto, and the README's own next steps say to reconcile with the completions series before trusting clearance." },
  ];
  const host = document.getElementById("pipeline");
  stages.forEach((s, i) => {
    const box = el("div", { class: "stage", role: "listitem" });
    box.appendChild(el("p", { class: "kicker", style: "margin:0 0 4px" }, `Step ${i + 1}`));
    box.appendChild(el("h3", { text: s.h }));
    box.appendChild(el("p", { class: "what", text: s.what }));
    const ul = el("ul", null, s.mods.map(mod).join("") + (s.note ? `<li>${s.note}</li>` : ""));
    box.appendChild(ul);
    host.appendChild(box);
  });
  const across = ["pipeline/schema.py", "pipeline/loaders.py", "pipeline/funnel.py", "pipeline/synthetic.py", "run_pilot.py"];
  document.getElementById("across").innerHTML =
    "<strong>Across all steps</strong><ul>" + across.map(mod).join("") + "</ul>";

  // Design decisions: plain summary (this site's wording) + README text.
  const plain = [
    "Use the zoning that applied when the application was filed, not today's zoning.",
    "Keep projects that needed a rezoning apart from those that did not.",
    "Group each development's many permits into one project before counting homes.",
    "Measure completion in a way that allows for projects that are still under way.",
  ];
  const dh = document.getElementById("design");
  p.design.forEach((d, i) => {
    const det = el("details", { class: "acc" });
    det.appendChild(el("summary", null, `<span class="num">${i + 1}</span><span class="head">${plain[i] || ""}</span>`));
    det.appendChild(el("div", { class: "body" }, `<blockquote><p>${d.html}</p></blockquote>`));
    dh.appendChild(det);
  });
  const terms = el("p", { class: "small", style: "margin-top:10px" },
    'Terms: <a class="term" data-term="as-of-right">as-of-right</a> · <a class="term" data-term="cumulative-incidence">cumulative incidence</a> · <a class="term" data-term="censoring">censoring</a> · <a class="term" data-term="aalen-johansen">Aalen-Johansen</a> · <a class="term" data-term="kaplan-meier">Kaplan-Meier</a> · <a class="term" data-term="cohort">cohort</a>');
  dh.appendChild(terms);

  document.getElementById("limitations").appendChild(renderList(p.limitations));
  document.getElementById("next").appendChild(renderList(p.next_steps, true));
  document.getElementById("assumptions").innerHTML = p.assumptions;
  document.getElementById("not-covered").innerHTML = `<span class="tag-unverified">Not tested</span>${p.audit_not_covered}`;
  document.getElementById("audit1").appendChild(renderList(p.audit_fixed, true));
  document.getElementById("audit2").appendChild(renderList(p.audit_checks));

  const L = p.links;
  document.getElementById("code-links").innerHTML = [
    `<li><a href="${L.readme}">phase2/README.md</a>: layout, design decisions and limitations.</li>`,
    `<li><a href="${L.audit}">phase2/AUDIT_LOG.md</a>: the two audits.</li>`,
    `<li><a href="${L.code}">phase2/pipeline/</a>: the modules themselves.</li>`,
  ].join("");
});
