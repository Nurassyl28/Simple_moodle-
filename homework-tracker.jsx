import React, { useState, useEffect, useMemo, useRef } from "react";
import {
  Plus, Check, X, Trash2, CalendarDays, NotebookPen, ChevronDown,
  AlertCircle, DownloadCloud, Upload, Undo2, Pencil, MapPin
} from "lucide-react";

const KEY = "hw-tracker-v1";
const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const DAYS_RU = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"];
const SHORT_RU = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"];
const MONTHS_RU = ["янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"];
const PALETTE = ["#2F5DE0", "#D14A32", "#17806A", "#7C4DD1", "#B87400", "#0F6E8C", "#B0286B", "#4F7A17"];
const TODO_COLOR = "#8A94A6";

const emptyData = () => ({
  tasks: [],
  timetable: DAYS.reduce((a, d) => ({ ...a, [d]: [] }), {}),
  seedV2: false,
});

/* расписание 2026-2027, 1 семестр */
const SEED = {
  Monday: [{ name: "CSS 109", time: "09:30", room: "F303" }, { name: "MAT 156", time: "12:30", room: "F202" }, { name: "MDE 003", time: "14:30", room: "I202" }],
  Tuesday: [{ name: "MDE 003", time: "08:30", room: "H203" }],
  Wednesday: [{ name: "MAT 156", time: "08:30", room: "D117" }, { name: "CSS 312", time: "10:30", room: "G304" }, { name: "CSS 112", time: "12:30", room: "E117" }],
  Thursday: [{ name: "CSS 112", time: "09:30", room: "F101" }, { name: "CSS 112", time: "13:30", room: "F203" }, { name: "MDE 160", time: "17:30", room: "F104" }],
  Friday: [{ name: "CSS 312", time: "08:30", room: "F108" }, { name: "MDE 003", time: "11:30", room: "H201" }, { name: "CSS 109", time: "15:30", room: "D113" }],
  Saturday: [],
  Sunday: [],
};

/* ---------- даты ---------- */
const iso = (d) => {
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
};
const fromIso = (s) => {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
};
const addDays = (d, n) => { const c = new Date(d); c.setDate(c.getDate() + n); return c; };
const dayIndex = (d) => (d.getDay() + 6) % 7;
const dayKey = (d) => DAYS[dayIndex(d)];
const pretty = (s) => {
  const d = fromIso(s);
  return `${SHORT_RU[dayIndex(d)]}, ${d.getDate()} ${MONTHS_RU[d.getMonth()]}`;
};
const daysBetween = (fromI, toI) => Math.round((fromIso(toI) - fromIso(fromI)) / 86400000);
const inWord = (n) => {
  if (n === 0) return "сегодня";
  if (n === 1) return "завтра";
  if (n === 2) return "послезавтра";
  const last = n % 10, two = n % 100;
  const w = two > 10 && two < 20 ? "дней" : last === 1 ? "день" : last >= 2 && last <= 4 ? "дня" : "дней";
  return `через ${n} ${w}`;
};
const agoWord = (n) => {
  if (n === 1) return "вчера";
  const last = n % 10, two = n % 100;
  const w = two > 10 && two < 20 ? "дней" : last === 1 ? "день" : last >= 2 && last <= 4 ? "дня" : "дней";
  return `${n} ${w} назад`;
};
const colorFor = (name) => {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
  return PALETTE[h % PALETTE.length];
};

/* ---------- нормализация расписания (старый формат — строки) ---------- */
const normTimetable = (tt = {}) => {
  const out = {};
  DAYS.forEach((d) => {
    out[d] = (tt[d] || []).map((x) => (typeof x === "string" ? { name: x } : { name: x.name, time: x.time || "", room: x.room || "" }));
    out[d].sort((a, b) => (a.time || "99").localeCompare(b.time || "99"));
  });
  return out;
};

function parseImport(raw) {
  const out = [];
  raw.split("\n").forEach((line) => {
    const l = line.trim();
    if (!l || l.startsWith("#")) return;
    const parts = l.split("|").map((s) => s.trim());
    let due = "", subject = "", text = "";
    if (parts.length >= 3) { [due, subject, text] = parts; }
    else if (parts.length === 2) { [due, text] = parts; }
    else return;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(due) || !text) return;
    out.push({ due, subject, text, kind: subject ? "hw" : "todo" });
  });
  return out;
}

const css = `
@import url('https://fonts.googleapis.com/css2?family=Golos+Text:wght@400;600;800&display=swap');

.hw { --ink:#16233B; --muted:#6C7A90; --paper:#FBFAF6; --line:#E3E1D9; --hl:#FFE24D; --red:#C0392B; --green:#1F7A5A;
  font-family:'Golos Text', ui-sans-serif, system-ui, -apple-system, sans-serif;
  color:var(--ink); background-color:var(--paper);
  background-image:linear-gradient(rgba(22,35,59,.05) 1px, transparent 1px), linear-gradient(90deg, rgba(22,35,59,.05) 1px, transparent 1px);
  background-size:26px 26px; min-height:100vh; -webkit-font-smoothing:antialiased;
}
.hw * { box-sizing:border-box; }
.hw button { font-family:inherit; cursor:pointer; border:none; background:none; color:inherit; }
.hw input, .hw textarea { font-family:inherit; font-size:16px; color:inherit; }
.wrap { max-width:520px; margin:0 auto; padding:20px 16px 150px; }

.top { display:flex; align-items:flex-start; justify-content:space-between; gap:10px; margin-bottom:22px; }
.top h1 { font-size:15px; font-weight:600; margin:0 0 2px; }
.top .count { font-size:13px; color:var(--muted); }
.top .count b { font-weight:600; color:var(--ink); }
.tools { display:flex; gap:6px; flex:none; }
.tool { display:flex; align-items:center; justify-content:center; width:34px; height:34px; color:var(--muted);
  border:1px solid var(--line); background:#fff; border-radius:10px; }
.tool:hover { color:var(--ink); border-color:var(--ink); }

.sect { margin-bottom:28px; }
.sect-head { display:flex; align-items:baseline; gap:10px; margin-bottom:12px; flex-wrap:wrap; }
.sect-head h2 { margin:0; font-size:26px; font-weight:800; letter-spacing:-.03em; line-height:1.1; }
.mark { position:relative; display:inline-block; }
.mark::before { content:""; position:absolute; left:-4px; right:-6px; bottom:1px; height:14px;
  background:var(--hl); border-radius:2px 8px 3px 7px; transform:rotate(-.7deg); z-index:0; }
.mark > span { position:relative; z-index:1; }
.sect-head .when { font-size:13px; color:var(--muted); font-weight:400; }
.sect-head.small h2 { font-size:16px; font-weight:600; letter-spacing:-.01em; }
.datehead { font-size:12.5px; color:var(--muted); margin:14px 0 7px; display:flex; gap:7px; align-items:baseline; }
.datehead b { font-weight:600; color:var(--ink); font-size:13px; }

.classes { display:flex; flex-direction:column; gap:5px; margin-bottom:13px; }
.cls { display:flex; align-items:center; gap:8px; font-size:13px; background:#fff; border:1px solid var(--line);
  border-radius:9px; padding:7px 11px; }
.cls .t { font-variant-numeric:tabular-nums; font-weight:600; font-size:12.5px; }
.cls .n { font-weight:600; }
.cls .r { color:var(--muted); font-size:12px; display:flex; align-items:center; gap:3px; margin-left:auto; }

.card { background:#fff; border:1px solid var(--line); border-radius:12px; overflow:hidden; }
.row { display:flex; align-items:flex-start; gap:11px; padding:12px 8px 12px 0; }
.row + .row { border-top:1px solid var(--line); }
.edge { width:4px; align-self:stretch; flex:none; border-radius:0 3px 3px 0; }
.tick { width:22px; height:22px; flex:none; margin-top:1px; border-radius:50%; border:1.5px solid #C9CCD2;
  display:flex; align-items:center; justify-content:center; background:#fff; transition:background .12s, border-color .12s; }
.tick.on { background:var(--green); border-color:var(--green); color:#fff; }
.body { flex:1; min-width:0; text-align:left; padding:0; }
.subj { font-size:11.5px; font-weight:600; letter-spacing:.02em; margin-bottom:2px; }
.txt { font-size:15px; line-height:1.35; word-break:break-word; }
.meta { font-size:12px; color:var(--muted); margin-top:3px; }
.meta.late { color:var(--red); }
.done .txt { text-decoration:line-through; color:var(--muted); }
.done .subj { color:var(--muted) !important; }
.acts { display:flex; flex-direction:column; gap:2px; flex:none; }
.act { opacity:.32; padding:4px; }
.act:hover { opacity:1; }
.act.d:hover { color:var(--red); }
.push { font-size:12px; color:var(--muted); border:1px solid var(--line); background:#fff;
  border-radius:999px; padding:4px 10px; margin-top:7px; }
.push:hover { border-color:var(--ink); color:var(--ink); }

.empty { border:1px dashed var(--line); border-radius:12px; padding:20px 16px; text-align:center; color:var(--muted); font-size:14px; }
.fold { display:flex; align-items:center; gap:7px; font-size:14px; color:var(--muted); padding:6px 0; }
.fold svg { transition:transform .15s; }
.fold.open svg { transform:rotate(180deg); }
.linkbtn { font-size:12.5px; color:var(--muted); text-decoration:underline; text-underline-offset:3px; }

.nav { position:fixed; left:0; right:0; bottom:0; background:rgba(251,250,246,.94); backdrop-filter:blur(8px);
  border-top:1px solid var(--line); display:flex; padding:8px 12px calc(8px + env(safe-area-inset-bottom)); gap:6px; justify-content:center; }
.nav button { flex:1; max-width:180px; display:flex; flex-direction:column; align-items:center; gap:3px;
  padding:7px 0; font-size:11px; color:var(--muted); border-radius:10px; }
.nav button.on { color:var(--ink); background:rgba(22,35,59,.06); }

.fab { position:fixed; right:max(18px, calc(50% - 244px)); bottom:calc(88px + env(safe-area-inset-bottom));
  width:54px; height:54px; border-radius:50%; background:var(--ink); color:var(--paper);
  display:flex; align-items:center; justify-content:center; box-shadow:0 6px 20px rgba(22,35,59,.28); }
.fab:active { transform:scale(.94); }

.undo { position:fixed; left:50%; transform:translateX(-50%); bottom:calc(96px + env(safe-area-inset-bottom));
  display:flex; align-items:center; gap:14px; background:var(--ink); color:var(--paper); border-radius:999px;
  padding:10px 12px 10px 18px; font-size:13.5px; box-shadow:0 6px 20px rgba(22,35,59,.3); z-index:40; max-width:92vw; }
.undo button { display:flex; align-items:center; gap:5px; font-weight:600; color:var(--hl); }

.scrim { position:fixed; inset:0; background:rgba(22,35,59,.32); display:flex; align-items:flex-end; justify-content:center; z-index:50; }
.sheet { width:100%; max-width:520px; background:var(--paper); border-radius:18px 18px 0 0;
  padding:18px 16px calc(20px + env(safe-area-inset-bottom)); max-height:88vh; overflow-y:auto; border-top:1px solid var(--line); }
.sheet h3 { margin:0; font-size:19px; font-weight:800; letter-spacing:-.02em; }
.sheet .hint { font-size:13px; color:var(--muted); line-height:1.5; margin:6px 0 14px; }
.label { font-size:12px; color:var(--muted); margin:16px 0 7px; }
.field { width:100%; padding:12px 13px; border:1px solid var(--line); border-radius:10px; background:#fff; outline:none; }
.field:focus { border-color:var(--ink); }
textarea.field { min-height:140px; resize:vertical; line-height:1.5; font-size:13.5px; }
.chips { display:flex; flex-wrap:wrap; gap:7px; }
.chip { font-size:13.5px; padding:8px 13px; border-radius:999px; border:1px solid var(--line); background:#fff; }
.chip.on { background:var(--ink); color:var(--paper); border-color:var(--ink); }
.chip.dim { color:var(--muted); }
.save { width:100%; margin-top:20px; padding:15px; border-radius:12px; background:var(--ink); color:var(--paper); font-size:16px; font-weight:600; }
.save:disabled { opacity:.35; }
.result { margin-top:12px; font-size:13.5px; color:var(--green); text-align:center; }
.result.bad { color:var(--red); }

.tt-day { border-bottom:1px solid var(--line); padding:12px 0; }
.tt-day:last-of-type { border-bottom:none; }
.tt-name { font-size:14px; font-weight:600; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center; }
.tt-name em { font-style:normal; font-size:12px; color:var(--muted); font-weight:400; }
.tt-item { display:flex; align-items:center; gap:9px; font-size:13.5px; padding:6px 0; }
.tt-item .t { font-variant-numeric:tabular-nums; color:var(--muted); font-size:12.5px; min-width:40px; }
.tt-item .r { color:var(--muted); font-size:12px; margin-left:auto; }
.tt-form { display:flex; gap:6px; margin-top:8px; }
.tt-form input { padding:8px 10px; border:1px solid var(--line); border-radius:8px; background:#fff; outline:none; font-size:14px; min-width:0; }
.banner { display:flex; gap:8px; align-items:center; font-size:13px; background:#FFF3E0; border:1px solid #F0D9A8; color:#7A5A12; padding:10px 12px; border-radius:10px; margin-bottom:16px; }
.danger { margin-top:26px; font-size:13px; color:var(--red); opacity:.8; }
@media (prefers-reduced-motion: reduce) { .hw * { transition:none !important; } }
`;

export default function HomeworkTracker() {
  const [data, setData] = useState(emptyData());
  const [loading, setLoading] = useState(true);
  const [saveErr, setSaveErr] = useState(false);
  const [tab, setTab] = useState("hw");
  const [sheet, setSheet] = useState(null);      // add | import | export | null
  const [editing, setEditing] = useState(null);  // задача на редактировании
  const [showDone, setShowDone] = useState(false);
  const [undo, setUndo] = useState(null);
  const undoTimer = useRef(null);

  /* ФИКС: дата пересчитывается, а не замирает на моменте открытия */
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const bump = () => setNow((p) => (iso(p) === iso(new Date()) ? p : new Date()));
    const t = setInterval(bump, 60000);
    document.addEventListener("visibilitychange", bump);
    return () => { clearInterval(t); document.removeEventListener("visibilitychange", bump); };
  }, []);

  const todayI = iso(now);
  const tomorrowI = iso(addDays(now, 1));

  useEffect(() => {
    (async () => {
      let next = emptyData();
      try {
        const r = await window.storage.get(KEY);
        if (r && r.value) {
          const p = JSON.parse(r.value);
          next = { ...emptyData(), ...p, timetable: normTimetable(p.timetable) };
        }
      } catch (e) { /* пусто */ }

      const noTimes = DAYS.every((d) => (next.timetable[d] || []).every((x) => !x.time));
      if (!next.seedV2 && noTimes) {
        next = { ...next, timetable: normTimetable(SEED), seedV2: true };
        try { await window.storage.set(KEY, JSON.stringify(next)); } catch (e) { /* позже */ }
      }
      setData(next);
      setLoading(false);
    })();
  }, []);

  const persist = async (next) => {
    setData(next);
    try { await window.storage.set(KEY, JSON.stringify(next)); setSaveErr(false); }
    catch (e) { setSaveErr(true); }
  };

  const newId = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  const toggle = (id) => persist({ ...data, tasks: data.tasks.map((t) => (t.id === id ? { ...t, done: !t.done } : t)) });
  const setDue = (id, due) => persist({ ...data, tasks: data.tasks.map((t) => (t.id === id ? { ...t, due } : t)) });

  /* ФИКС: удаление можно отменить */
  const remove = (id) => {
    const gone = data.tasks.find((t) => t.id === id);
    persist({ ...data, tasks: data.tasks.filter((t) => t.id !== id) });
    setUndo(gone);
    clearTimeout(undoTimer.current);
    undoTimer.current = setTimeout(() => setUndo(null), 7000);
  };
  const restore = () => {
    if (undo) persist({ ...data, tasks: [...data.tasks, undo] });
    setUndo(null);
  };

  const saveTask = (t) => {
    if (t.id) persist({ ...data, tasks: data.tasks.map((x) => (x.id === t.id ? { ...x, ...t } : x)) });
    else persist({ ...data, tasks: [...data.tasks, { ...t, id: newId() }] });
    setSheet(null); setEditing(null);
  };

  const importTasks = (list) => {
    const seen = new Set(data.tasks.map((t) => `${t.due}|${(t.subject || "").toLowerCase()}|${t.text.toLowerCase()}`));
    const fresh = []; let skipped = 0;
    list.forEach((t) => {
      const k = `${t.due}|${(t.subject || "").toLowerCase()}|${t.text.toLowerCase()}`;
      if (seen.has(k)) { skipped++; return; }
      seen.add(k); fresh.push({ ...t, id: newId(), done: false });
    });
    if (fresh.length) persist({ ...data, tasks: [...data.tasks, ...fresh] });
    return { added: fresh.length, skipped };
  };

  const clearDone = () => persist({ ...data, tasks: data.tasks.filter((t) => !t.done) });

  const subjects = useMemo(() => {
    const s = new Set();
    DAYS.forEach((d) => (data.timetable[d] || []).forEach((x) => s.add(x.name)));
    data.tasks.forEach((t) => t.subject && s.add(t.subject));
    return [...s];
  }, [data]);

  const open = data.tasks.filter((t) => !t.done);
  const done = data.tasks.filter((t) => t.done);
  const overdue = open.filter((t) => t.due && t.due < todayI).sort((a, b) => a.due.localeCompare(b.due));
  const dueToday = open.filter((t) => t.due === todayI);
  const dueTomorrow = open.filter((t) => t.due === tomorrowI);
  const later = open.filter((t) => t.due && t.due > tomorrowI).sort((a, b) => a.due.localeCompare(b.due));
  const undated = open.filter((t) => !t.due);
  const classesTomorrow = data.timetable[dayKey(addDays(now, 1))] || [];

  const laterGroups = useMemo(() => {
    const g = [];
    later.forEach((t) => {
      const last = g[g.length - 1];
      if (last && last.due === t.due) last.items.push(t);
      else g.push({ due: t.due, items: [t] });
    });
    return g;
  }, [later]);

  const rowProps = {
    onToggle: toggle,
    onDelete: remove,
    onEdit: (t) => { setEditing(t); setSheet("add"); },
  };

  if (loading) {
    return (
      <div className="hw"><style>{css}</style>
        <div className="wrap"><p style={{ color: "#6C7A90", fontSize: 14 }}>Открываю тетрадь…</p></div>
      </div>
    );
  }

  return (
    <div className="hw">
      <style>{css}</style>
      <div className="wrap">
        <div className="top">
          <div>
            <h1>{DAYS_RU[dayIndex(now)]}, {now.getDate()} {MONTHS_RU[now.getMonth()]}</h1>
            {/* ФИКС: счётчик показывает ближайшее, а не всё подряд */}
            <div className="count">
              сегодня <b>{dueToday.length}</b> · завтра <b>{dueTomorrow.length}</b>
              {overdue.length > 0 && <> · <b style={{ color: "#C0392B" }}>просрочено {overdue.length}</b></>}
            </div>
          </div>
          <div className="tools">
            <button className="tool" onClick={() => setSheet("import")} title="Импорт"><DownloadCloud size={16} /></button>
            <button className="tool" onClick={() => setSheet("export")} title="Выгрузить всё"><Upload size={16} /></button>
          </div>
        </div>

        {saveErr && <div className="banner"><AlertCircle size={15} /> Не получилось сохранить. Проверь интернет.</div>}

        {tab === "hw" ? (
          <>
            {overdue.length > 0 && (
              <div className="sect">
                <div className="sect-head"><h2 style={{ color: "#C0392B" }}>Просрочено</h2></div>
                <List tasks={overdue} {...rowProps} today={todayI} showDate onPush={(id) => setDue(id, todayI)} />
              </div>
            )}

            <div className="sect">
              <div className="sect-head"><h2>Сегодня</h2></div>
              {dueToday.length
                ? <List tasks={dueToday} {...rowProps} today={todayI} />
                : <div className="empty">На сегодня ничего.</div>}
            </div>

            <div className="sect">
              <div className="sect-head">
                <h2 className="mark"><span>Завтра</span></h2>
                <span className="when">{pretty(tomorrowI)}</span>
              </div>
              {/* ФИКС: пары со временем и аудиторией */}
              {classesTomorrow.length > 0 && (
                <div className="classes">
                  {classesTomorrow.map((c, i) => (
                    <div className="cls" key={i}>
                      {c.time && <span className="t">{c.time}</span>}
                      <span className="n" style={{ color: colorFor(c.name) }}>{c.name}</span>
                      {c.room && <span className="r"><MapPin size={11} />{c.room}</span>}
                    </div>
                  ))}
                </div>
              )}
              {dueTomorrow.length
                ? <List tasks={dueTomorrow} {...rowProps} today={todayI} />
                : <div className="empty">На завтра пока ничего не записано.</div>}
            </div>

            {laterGroups.length > 0 && (
              <div className="sect">
                <div className="sect-head small"><h2>Дальше</h2></div>
                {/* ФИКС: сгруппировано по датам, а не свалено в кучу */}
                {laterGroups.map((g) => (
                  <div key={g.due}>
                    <div className="datehead"><b>{pretty(g.due)}</b> <span>{inWord(daysBetween(todayI, g.due))}</span></div>
                    <List tasks={g.items} {...rowProps} today={todayI} />
                  </div>
                ))}
              </div>
            )}

            {undated.length > 0 && (
              <div className="sect">
                <div className="sect-head small"><h2>Без даты</h2></div>
                <List tasks={undated} {...rowProps} today={todayI} />
              </div>
            )}

            {done.length > 0 && (
              <div className="sect">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <button className={"fold" + (showDone ? " open" : "")} onClick={() => setShowDone(!showDone)}>
                    <ChevronDown size={15} /> Сделано · {done.length}
                  </button>
                  {showDone && <button className="linkbtn" onClick={clearDone}>очистить</button>}
                </div>
                {showDone && <List tasks={done} {...rowProps} today={todayI} showDate />}
              </div>
            )}
          </>
        ) : (
          <Timetable data={data} persist={persist} now={now} />
        )}
      </div>

      {tab === "hw" && !sheet && (
        <button className="fab" onClick={() => { setEditing(null); setSheet("add"); }} aria-label="Добавить"><Plus size={26} /></button>
      )}

      {undo && !sheet && (
        <div className="undo">
          <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>Удалено: {undo.text}</span>
          <button onClick={restore}><Undo2 size={15} /> Вернуть</button>
        </div>
      )}

      <div className="nav">
        <button className={tab === "hw" ? "on" : ""} onClick={() => setTab("hw")}><NotebookPen size={19} /> Домашка</button>
        <button className={tab === "tt" ? "on" : ""} onClick={() => setTab("tt")}><CalendarDays size={19} /> Расписание</button>
      </div>

      {sheet === "add" && (
        <AddSheet onClose={() => { setSheet(null); setEditing(null); }} onSave={saveTask}
          subjects={subjects} timetable={data.timetable} now={now} initial={editing} />
      )}
      {sheet === "import" && <ImportSheet onClose={() => setSheet(null)} onImport={importTasks} />}
      {sheet === "export" && <ExportSheet onClose={() => setSheet(null)} tasks={data.tasks} />}
    </div>
  );
}

function List({ tasks, onToggle, onDelete, onEdit, onPush, showDate, today }) {
  return (
    <div className="card">
      {tasks.map((t) => {
        const isTodo = t.kind === "todo" || (!t.subject && t.kind !== "hw");
        const c = isTodo ? TODO_COLOR : colorFor(t.subject || "—");
        const late = t.due && t.due < today && !t.done;
        return (
          <div className={"row" + (t.done ? " done" : "")} key={t.id}>
            <div className="edge" style={{ background: t.done ? "#D7D9DE" : c }} />
            <button className={"tick" + (t.done ? " on" : "")} onClick={() => onToggle(t.id)}
              aria-label={t.done ? "Вернуть в невыполненные" : "Отметить как сделано"}>
              {t.done && <Check size={13} strokeWidth={3} />}
            </button>
            {/* ФИКС: тап по задаче открывает редактирование */}
            <button className="body" onClick={() => onEdit(t)}>
              <div className="subj" style={{ color: c }}>{isTodo ? "Дело" : t.subject}</div>
              <div className="txt">{t.text}</div>
              {(showDate || late) && t.due && (
                <div className={"meta" + (late ? " late" : "")}>
                  {pretty(t.due)}{late ? ` · ${agoWord(daysBetween(t.due, today))}` : ""}
                </div>
              )}
            </button>
            <div className="acts">
              <button className="act" onClick={() => onEdit(t)} aria-label="Изменить"><Pencil size={14} /></button>
              <button className="act d" onClick={() => onDelete(t.id)} aria-label="Удалить"><Trash2 size={14} /></button>
            </div>
          </div>
        );
      })}
      {/* ФИКС: просроченное можно перенести одной кнопкой */}
      {onPush && (
        <div style={{ padding: "0 12px 12px 12px" }}>
          <button className="push" onClick={() => tasks.forEach((t) => onPush(t.id))}>
            Перенести всё на сегодня
          </button>
        </div>
      )}
    </div>
  );
}

function AddSheet({ onClose, onSave, subjects, timetable, now, initial }) {
  const [kind, setKind] = useState(initial?.kind || (initial && !initial.subject ? "todo" : "hw"));
  const [subject, setSubject] = useState(initial?.subject || "");
  const [custom, setCustom] = useState("");
  const [text, setText] = useState(initial?.text || "");
  const [due, setDue] = useState(initial?.due || iso(addDays(now, 1)));
  const inputRef = useRef(null);
  useEffect(() => { inputRef.current?.focus(); }, []);

  const chosen = custom.trim() || subject;

  /* ФИКС: сначала предметы, которые есть в этот день по расписанию */
  const onThatDay = useMemo(() => {
    if (!due) return [];
    const d = fromIso(due);
    return [...new Set((timetable[dayKey(d)] || []).map((x) => x.name))];
  }, [due, timetable]);
  const rest = subjects.filter((s) => !onThatDay.includes(s));

  const nextLesson = useMemo(() => {
    if (!chosen) return null;
    for (let i = 1; i <= 14; i++) {
      const d = addDays(now, i);
      if ((timetable[dayKey(d)] || []).some((x) => x.name.toLowerCase() === chosen.toLowerCase())) return iso(d);
    }
    return null;
  }, [chosen, timetable, now]);

  const quick = [
    { label: "Сегодня", v: iso(now) },
    { label: "Завтра", v: iso(addDays(now, 1)) },
    ...(nextLesson && nextLesson !== iso(addDays(now, 1))
      ? [{ label: `След. ${chosen} · ${pretty(nextLesson)}`, v: nextLesson }] : []),
    { label: pretty(iso(addDays(now, 2))), v: iso(addDays(now, 2)) },
    { label: pretty(iso(addDays(now, 3))), v: iso(addDays(now, 3)) },
  ];

  const submit = () => {
    if (!text.trim()) return;
    onSave({ ...(initial?.id ? { id: initial.id } : {}), text: text.trim(), subject: kind === "hw" ? chosen : "", kind, due, done: initial?.done || false });
  };

  const pick = (s) => { setSubject(subject === s ? "" : s); setCustom(""); };

  return (
    <div className="scrim" onClick={onClose}>
      <div className="sheet" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 14 }}>
          <h3>{initial ? "Изменить" : kind === "hw" ? "Новая домашка" : "Новое дело"}</h3>
          <button onClick={onClose} style={{ opacity: .5 }} aria-label="Закрыть"><X size={20} /></button>
        </div>

        <div className="chips" style={{ marginBottom: 14 }}>
          <button className={"chip" + (kind === "hw" ? " on" : "")} onClick={() => setKind("hw")}>Домашка</button>
          <button className={"chip" + (kind === "todo" ? " on" : "")} onClick={() => setKind("todo")}>Дело</button>
        </div>

        {/* ФИКС: Enter сохраняет */}
        <input ref={inputRef} className="field"
          placeholder={kind === "hw" ? "например: стр. 45, упр. 3–7" : "например: сдать книгу в библиотеку"}
          value={text} onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") submit(); }} />

        <div className="label">Срок</div>
        <div className="chips">
          {quick.map((q) => (
            <button key={q.label} className={"chip" + (due === q.v ? " on" : "")} onClick={() => setDue(q.v)}>{q.label}</button>
          ))}
        </div>
        <input type="date" className="field" style={{ marginTop: 8 }} value={due} onChange={(e) => setDue(e.target.value)} />

        {kind === "hw" && (
          <>
            <div className="label">
              {onThatDay.length ? `Предметы в этот день — ${pretty(due)}` : "Предмет"}
            </div>
            <div className="chips">
              {onThatDay.map((s) => (
                <button key={s} className={"chip" + (subject === s && !custom ? " on" : "")} onClick={() => pick(s)}>{s}</button>
              ))}
            </div>
            {rest.length > 0 && (
              <>
                <div className="label" style={{ marginTop: 12 }}>Остальные</div>
                <div className="chips">
                  {rest.map((s) => (
                    <button key={s} className={"chip dim" + (subject === s && !custom ? " on" : "")} onClick={() => pick(s)}>{s}</button>
                  ))}
                </div>
              </>
            )}
            <input className="field" style={{ marginTop: 10 }} placeholder="или впиши другой предмет"
              value={custom} onChange={(e) => { setCustom(e.target.value); setSubject(""); }} />
          </>
        )}

        <button className="save" disabled={!text.trim()} onClick={submit}>
          {initial ? "Сохранить" : "Добавить в список"}
        </button>
      </div>
    </div>
  );
}

function ImportSheet({ onClose, onImport }) {
  const [raw, setRaw] = useState("");
  const [res, setRes] = useState(null);
  const parsed = useMemo(() => parseImport(raw), [raw]);
  return (
    <div className="scrim" onClick={onClose}>
      <div className="sheet" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <h3>Импорт</h3>
          <button onClick={onClose} style={{ opacity: .5 }} aria-label="Закрыть"><X size={20} /></button>
        </div>
        <p className="hint">Одна строка — одно задание:<br /><code style={{ fontSize: 12.5 }}>2026-09-09 | CSS 112 | Лаба 2</code></p>
        <textarea className="field" value={raw} onChange={(e) => { setRaw(e.target.value); setRes(null); }}
          placeholder="2026-09-09 | CSS 112 | Лаба 2&#10;2026-09-11 | MAT 156 | Задачи 1-10" />
        <button className="save" disabled={!parsed.length} onClick={() => { setRes(onImport(parsed)); setRaw(""); }}>
          {parsed.length ? `Добавить ${parsed.length}` : "Добавить"}
        </button>
        {raw.trim() && !parsed.length && <div className="result bad">Формат: дата | предмет | задание</div>}
        {res && <div className="result">Добавлено: {res.added}{res.skipped ? ` · пропущено: ${res.skipped}` : ""}</div>}
      </div>
    </div>
  );
}

/* ФИКС: можно выгрузить всё и не потерять */
function ExportSheet({ onClose, tasks }) {
  const text = useMemo(() =>
    tasks.filter((t) => t.due).sort((a, b) => a.due.localeCompare(b.due))
      .map((t) => `${t.due} | ${t.subject || ""} | ${t.text}${t.done ? "   (сделано)" : ""}`).join("\n"),
    [tasks]);
  const [copied, setCopied] = useState(false);
  return (
    <div className="scrim" onClick={onClose}>
      <div className="sheet" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <h3>Выгрузка</h3>
          <button onClick={onClose} style={{ opacity: .5 }} aria-label="Закрыть"><X size={20} /></button>
        </div>
        <p className="hint">Копия всех записей. Сохрани куда-нибудь, если боишься потерять.</p>
        <textarea className="field" readOnly value={text || "Пока пусто."} onFocus={(e) => e.target.select()} />
        <button className="save" onClick={async () => {
          try { await navigator.clipboard.writeText(text); setCopied(true); } catch (e) { setCopied(false); }
        }}>Скопировать</button>
        {copied && <div className="result">Скопировано</div>}
      </div>
    </div>
  );
}

function Timetable({ data, persist, now }) {
  const [openDay, setOpenDay] = useState(null);
  const [f, setF] = useState({ name: "", time: "", room: "" });

  const add = (day) => {
    const name = f.name.trim();
    if (!name) return;
    const list = data.timetable[day] || [];
    /* ФИКС: не даём добавить один и тот же предмет в то же время дважды */
    if (list.some((x) => x.name.toLowerCase() === name.toLowerCase() && (x.time || "") === f.time)) {
      setF({ name: "", time: "", room: "" }); return;
    }
    const next = [...list, { name, time: f.time.trim(), room: f.room.trim() }]
      .sort((a, b) => (a.time || "99").localeCompare(b.time || "99"));
    persist({ ...data, timetable: { ...data.timetable, [day]: next } });
    setF({ name: "", time: "", room: "" });
  };
  const del = (day, i) =>
    persist({ ...data, timetable: { ...data.timetable, [day]: data.timetable[day].filter((_, j) => j !== i) } });

  const wipe = () => {
    if (!window.confirm("Удалить всю домашку и расписание? Вернуть будет нельзя.")) return;
    persist({ ...emptyData(), seedV2: true });
  };

  const todayKey = dayKey(now);

  return (
    <>
      <div className="sect-head" style={{ marginBottom: 4 }}><h2>Расписание</h2></div>
      <p style={{ fontSize: 13.5, color: "#6C7A90", margin: "0 0 18px", lineHeight: 1.5 }}>
        Нажми на день, чтобы добавить пару. Время и аудитория необязательны.
      </p>

      <div className="card" style={{ padding: "4px 14px" }}>
        {DAYS.map((day, i) => (
          <div className="tt-day" key={day}>
            <div className="tt-name">
              <span>{DAYS_RU[i]} {day === todayKey && <em>сегодня</em>}</span>
              <button className="linkbtn" onClick={() => { setOpenDay(openDay === day ? null : day); setF({ name: "", time: "", room: "" }); }}>
                {openDay === day ? "закрыть" : "+ пара"}
              </button>
            </div>

            {(data.timetable[day] || []).map((x, j) => (
              <div className="tt-item" key={j}>
                <span className="t">{x.time || "—"}</span>
                <span style={{ color: colorFor(x.name), fontWeight: 600 }}>{x.name}</span>
                {x.room && <span className="r">{x.room}</span>}
                <button onClick={() => del(day, j)} style={{ opacity: .35, display: "flex", marginLeft: x.room ? 8 : "auto" }} aria-label="Убрать">
                  <X size={14} />
                </button>
              </div>
            ))}
            {!(data.timetable[day] || []).length && openDay !== day && (
              <div style={{ fontSize: 13, color: "#6C7A90" }}>—</div>
            )}

            {openDay === day && (
              <div className="tt-form">
                <input style={{ flex: 2 }} placeholder="CSS 112" value={f.name} autoFocus
                  onChange={(e) => setF({ ...f, name: e.target.value })}
                  onKeyDown={(e) => { if (e.key === "Enter") add(day); }} />
                <input style={{ flex: 1 }} placeholder="09:30" value={f.time}
                  onChange={(e) => setF({ ...f, time: e.target.value })}
                  onKeyDown={(e) => { if (e.key === "Enter") add(day); }} />
                <input style={{ flex: 1 }} placeholder="F101" value={f.room}
                  onChange={(e) => setF({ ...f, room: e.target.value })}
                  onKeyDown={(e) => { if (e.key === "Enter") add(day); }} />
                <button onClick={() => add(day)} style={{ padding: "0 12px", fontWeight: 600 }}>OK</button>
              </div>
            )}
          </div>
        ))}
      </div>

      <button className="danger" onClick={wipe}>Удалить всё</button>
    </>
  );
}
