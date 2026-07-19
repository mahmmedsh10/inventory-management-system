/* ============ سجل المخزن — سكربتات الواجهة ============ */

/* تطبيع النص العربي: أ/إ/آ = ا ، ة = ه ، ى = ي ، وإزالة التشكيل */
function normalizeAr(s) {
  return (s || "")
    .toLowerCase()
    .replace(/[\u064B-\u0652\u0640]/g, "")
    .replace(/[أإآ]/g, "ا")
    .replace(/ة/g, "ه")
    .replace(/ى/g, "ي")
    .trim();
}

/* مطابقة متعددة الكلمات بالبادئة: "m r" تطابق عنصراً كلمته الأولى تبدأ بـ m والثانية بـ r بالترتيب */
function multiWordPrefixMatch(query, text) {
  const qWords = normalizeAr(query).split(/\s+/).filter(Boolean);
  const tWords = normalizeAr(text).split(/\s+/).filter(Boolean);
  if (!qWords.length) return true;
  let ti = 0;
  for (const qw of qWords) {
    let found = false;
    while (ti < tWords.length) {
      if (tWords[ti].startsWith(qw)) { found = true; ti++; break; }
      ti++;
    }
    if (!found) return false;
  }
  return true;
}

/* ============ بحث الجداول (صفحة الأصناف وغيرها) ============ */
document.querySelectorAll("[data-table-search]").forEach(function (input) {
  const table = document.querySelector(input.dataset.tableSearch);
  const counter = document.querySelector(input.dataset.searchCount || null);
  if (!table) return;
  input.addEventListener("input", function () {
    let visible = 0;
    table.querySelectorAll("tbody tr").forEach(function (tr) {
      const name = tr.dataset.searchText || tr.textContent;
      const show = multiWordPrefixMatch(input.value, name);
      tr.style.display = show ? "" : "none";
      if (show) visible++;
    });
    if (counter) counter.textContent = "النتائج: " + visible;
  });
});

/* ============ عدّادات الكمية ============ */
document.addEventListener("click", function (e) {
  const btn = e.target.closest("[data-step]");
  if (!btn) return;
  e.preventDefault();
  const input = btn.parentElement.querySelector("input");
  const step = parseInt(btn.dataset.step, 10);
  const min = input.min !== "" ? parseInt(input.min, 10) : 0;
  let val = parseInt(input.value, 10);
  if (isNaN(val)) val = min;
  val += step;
  if (val < min) val = min;
  input.value = val;
  input.dispatchEvent(new Event("change"));
});

/* ============ الكومبوبوكس القابل للبحث ============ */
function initCombo(wrap) {
  const input = wrap.querySelector("input[type=text]");
  const hidden = wrap.querySelector("input[type=hidden]");
  const list = wrap.querySelector(".combo-list");
  const options = JSON.parse(wrap.dataset.options || "[]"); /* [{id, name, qty?}] */
  const quickAddUrl = wrap.dataset.quickAdd || null;
  const quickAddField = wrap.dataset.quickAddField || null;
  const showQty = wrap.dataset.showQty === "1";

  function render() {
    const q = input.value;
    list.innerHTML = "";
    let shown = 0;
    options.forEach(function (opt) {
      if (!multiWordPrefixMatch(q, opt.name)) return;
      shown++;
      const div = document.createElement("div");
      div.textContent = opt.name;
      if (showQty) {
        const tag = document.createElement("span");
        tag.className = "qty-tag";
        tag.textContent = " (المتاح: " + opt.qty + ")";
        div.appendChild(tag);
        if (opt.qty <= 0) div.classList.add("out");
      }
      div.addEventListener("mousedown", function (e) {
        e.preventDefault();
        select(opt);
      });
      list.appendChild(div);
    });
    if (quickAddUrl && q.trim()) {
      const add = document.createElement("div");
      add.className = "add-new";
      add.textContent = "+ إضافة «" + q.trim() + "» كجديد";
      add.addEventListener("mousedown", function (e) {
        e.preventDefault();
        quickAdd(q.trim());
      });
      list.appendChild(add);
    }
    list.classList.toggle("open", shown > 0 || (quickAddUrl && q.trim() !== ""));
  }

  function select(opt) {
    input.value = opt.name;
    hidden.value = opt.id;
    list.classList.remove("open");
    input.dispatchEvent(new CustomEvent("combo:select", { detail: opt, bubbles: true }));
  }

  function quickAdd(name) {
    const body = {};
    body[quickAddField] = name;
    fetch(quickAddUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) { alert(data.error || "خطأ"); return; }
        const opt = { id: data.item_id || data.supplier_id, name: name, qty: 0 };
        options.push(opt);
        select(opt);
      })
      .catch(function () { alert("تعذر الاتصال بالخادم"); });
  }

  input.addEventListener("input", function () { hidden.value = ""; render(); });
  input.addEventListener("focus", render);
  input.addEventListener("blur", function () {
    setTimeout(function () { list.classList.remove("open"); }, 150);
  });
}
document.querySelectorAll(".combo").forEach(initCombo);

/* ============ صفوف الفواتير الديناميكية ============ */
function initInvoiceRows(container) {
  const tmpl = document.getElementById(container.dataset.rowTemplate);
  const addBtn = document.querySelector(container.dataset.addBtn);
  function addRow(prefillName, prefillId, prefillQty) {
    const node = tmpl.content.cloneNode(true);
    container.appendChild(node);
    const row = container.lastElementChild;
    row.querySelectorAll(".combo").forEach(initCombo);
    if (prefillId) {
      row.querySelector(".combo input[type=hidden]").value = prefillId;
      row.querySelector(".combo input[type=text]").value = prefillName;
    }
    if (prefillQty) row.querySelector("input[name='quantity[]']").value = prefillQty;
    row.querySelector(".remove-row").addEventListener("click", function (e) {
      e.preventDefault();
      row.remove();
    });
  }
  if (addBtn) addBtn.addEventListener("click", function (e) { e.preventDefault(); addRow(); });
  container.querySelectorAll(".invoice-row .remove-row").forEach(function (b) {
    b.addEventListener("click", function (e) { e.preventDefault(); b.closest(".invoice-row").remove(); });
  });
  /* prefill من رابط تنبيه */
  if (container.dataset.prefillId) {
    addRow(container.dataset.prefillName, container.dataset.prefillId, container.dataset.prefillQty);
  } else if (!container.querySelector(".invoice-row")) {
    addRow();
  }
}
document.querySelectorAll("[data-row-template]").forEach(initInvoiceRows);
