/**
 * ============================================================
 * سجل المخزن — سكربتات الواجهة (Frontend Scripts)
 * ============================================================
 * الملف مقسَّم إلى أقسام مستقلة، كل قسم مسؤول عن سلوك واجهة واحد:
 *   1) أدوات تطبيع ومطابقة النص العربي (Arabic Search Utils)
 *   2) بحث الجداول (Table Search)
 *   3) عدّادات الكمية (Quantity Steppers)
 *   4) الكومبوبوكس القابل للبحث (Searchable Combobox)
 *   5) صفوف الفواتير الديناميكية (Dynamic Invoice Rows)
 *
 * لا يوجد أي تغيير في السلوك مقارنة بالنسخة السابقة — التعديل هنا
 * تنظيمي وتوثيقي فقط (تقسيم لأقسام، وإضافة تعليقات JSDoc توضيحية).
 * ============================================================
 */

/* ============================================================
 * 1) أدوات تطبيع ومطابقة النص العربي
 * ============================================================ */

/**
 * تُطبِّع نصاً عربياً لتسهيل المطابقة بغض النظر عن اختلافات الكتابة
 * الشائعة: توحيد أشكال الألف (أ/إ/آ → ا)، توحيد التاء المربوطة
 * والهاء (ة → ه)، توحيد الألف المقصورة والياء (ى → ي)، وإزالة
 * علامات التشكيل (الحركات) والتطويل، مع تحويل الأحرف اللاتينية
 * لحالة صغيرة لدعم البحث بالحروف الإنجليزية أيضاً.
 *
 * @param {string} s النص المُدخَل (قد يكون فارغاً أو undefined).
 * @returns {string} النص بعد التطبيع والتقليم (trim).
 */
function normalizeAr(s) {
  return (s || "")
    .toLowerCase()
    .replace(/[\u064B-\u0652\u0640]/g, "")
    .replace(/[أإآ]/g, "ا")
    .replace(/ة/g, "ه")
    .replace(/ى/g, "ي")
    .trim();
}

/**
 * مطابقة متعددة الكلمات بالبادئة (Multi-word Prefix Match).
 * تدعم اختصارات البحث مثل "م ر" لمطابقة عنصر تبدأ كلمته الأولى
 * بـ"م" وكلمته الثانية بـ"ر" بنفس الترتيب — وهي ميزة بحث سريع
 * شائعة في الشاشات العربية (البحث عن "مخزن رئيسي" بكتابة "م ر" مثلاً).
 *
 * @param {string} query نص البحث المكتوب من المستخدم.
 * @param {string} text النص المراد مطابقته (اسم صنف، مورد، ...).
 * @returns {boolean} true إذا طابق كل جزء من الاستعلام كلمة متتالية
 *                     في النص بنفس الترتيب، أو إذا كان الاستعلام فارغاً.
 */
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

/* ============================================================
 * 2) بحث الجداول (صفحة الأصناف، الموردين، العملاء، ...)
 * ============================================================
 * أي حقل إدخال يحمل السمة data-table-search="#selector" يُفعَّل
 * تلقائياً كمربع بحث فوري (Live Search) على جدول بنفس الصفحة،
 * ويُظهر/يُخفي صفوف <tbody> حسب مطابقة multiWordPrefixMatch.
 */
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

/* ============================================================
 * 3) عدّادات الكمية (Quantity Steppers)
 * ============================================================
 * أي زر يحمل السمة data-step="1" أو data-step="-1" داخل عنصر
 * .stepper يزيد/ينقص قيمة حقل الرقم المجاور له عند الضغط، مع
 * احترام الحد الأدنى (min) المضبوط على الحقل.
 */
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

/* ============================================================
 * 4) الكومبوبوكس القابل للبحث (Searchable Combobox)
 * ============================================================
 * عنصر .combo يجمع حقل نص ظاهر + حقل hidden يحمل المعرّف الفعلي
 * (item_id، supplier_id، ...) + قائمة خيارات منسدلة قابلة للبحث
 * بنفس منطق multiWordPrefixMatch، مع دعم اختياري لـ"إضافة سريعة"
 * (Quick Add) عبر AJAX عندما لا يوجد خيار مطابق للنص المكتوب.
 */

/**
 * تُفعِّل سلوك الكومبوبوكس على عنصر واحد يحمل الكلاس .combo.
 *
 * السمات (data-*) المتوقعة على العنصر:
 *  - data-options   : مصفوفة JSON بصيغة [{id, name, qty?}, ...]
 *  - data-quick-add  : رابط AJAX اختياري لإضافة خيار جديد سريعاً
 *  - data-quick-add-field : اسم الحقل المُرسَل في جسم طلب الإضافة السريعة
 *  - data-show-qty   : "1" لعرض الكمية المتاحة أمام كل خيار (لأصناف المخزون)
 *
 * @param {HTMLElement} wrap عنصر .combo المراد تفعيله.
 * @returns {void}
 */
function initCombo(wrap) {
  const input = wrap.querySelector("input[type=text]");
  const hidden = wrap.querySelector("input[type=hidden]");
  const list = wrap.querySelector(".combo-list");
  const options = JSON.parse(wrap.dataset.options || "[]"); /* [{id, name, qty?}] */
  const quickAddUrl = wrap.dataset.quickAdd || null;
  const quickAddField = wrap.dataset.quickAddField || null;
  const showQty = wrap.dataset.showQty === "1";

  /** يعيد رسم قائمة الخيارات المطابقة لنص البحث الحالي. */
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

  /**
   * يختار خياراً من القائمة: يملأ الحقل الظاهر والحقل المخفي، ويطلق
   * حدثاً مخصصاً combo:select يمكن لأي كود آخر الاستماع إليه (تستخدمه
   * صفوف الفواتير الديناميكية لمعرفة متى تغيّر الصنف المختار).
   * @param {{id:*, name:string, qty?:number}} opt الخيار المُختار.
   */
  function select(opt) {
    input.value = opt.name;
    hidden.value = opt.id;
    list.classList.remove("open");
    input.dispatchEvent(new CustomEvent("combo:select", { detail: opt, bubbles: true }));
  }

  /**
   * يرسل طلب "إضافة سريعة" عبر AJAX للخادم (صنف أو مورد جديد)، ثم
   * يضيف الخيار الجديد لقائمة الخيارات المحلية ويختاره تلقائياً.
   * @param {string} name الاسم المكتوب المُراد إضافته كخيار جديد.
   */
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

/* ============================================================
 * 5) صفوف الفواتير الديناميكية (Dynamic Invoice Rows)
 * ============================================================
 * حاوية تحمل data-row-template (معرّف عنصر <template>) وdata-add-btn
 * (محدد زر "إضافة صف") تدعم إضافة/حذف صفوف صنف بشكل ديناميكي في
 * نماذج فواتير الشراء والصرف وأذونات الإعدام، مع دعم التعبئة المسبقة
 * لأول صف عند الفتح من رابط تنبيه (مثل تنبيه صلاحية بلوحة التحكم).
 */

/**
 * تُفعِّل حاوية صفوف فاتورة واحدة: تربط زر الإضافة، وتُفعِّل كل
 * كومبوبوكس داخل الصفوف الموجودة مسبقاً، وتضيف صفاً افتراضياً واحداً
 * فارغاً (أو مُعبَّأً مسبقاً) إذا كانت الحاوية فارغة تماماً.
 *
 * @param {HTMLElement} container حاوية الصفوف (عادة عنصر #rows).
 * @returns {void}
 */
function initInvoiceRows(container) {
  const tmpl = document.getElementById(container.dataset.rowTemplate);
  const addBtn = document.querySelector(container.dataset.addBtn);

  /**
   * يضيف صفاً جديداً لحاوية الصفوف، مع تعبئة اختيارية للصنف والكمية.
   * @param {string} [prefillName] اسم الصنف المعروض مسبقاً (إن وُجد).
   * @param {string|number} [prefillId] معرّف الصنف المعروض مسبقاً.
   * @param {string|number} [prefillQty] الكمية المقترحة مسبقاً.
   */
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

  /* تعبئة مسبقة عند الفتح من رابط تنبيه (مثل تنبيه صلاحية بلوحة التحكم) */
  if (container.dataset.prefillId) {
    addRow(container.dataset.prefillName, container.dataset.prefillId, container.dataset.prefillQty);
  } else if (!container.querySelector(".invoice-row")) {
    addRow();
  }
}
document.querySelectorAll("[data-row-template]").forEach(initInvoiceRows);
