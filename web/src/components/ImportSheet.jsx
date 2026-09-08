import { useState } from "react";
import { X } from "lucide-react";
import { api } from "../api";

/** Импорт строк «дата | предмет | задание». Разбор делает бэкенд. */
export default function ImportSheet({ onClose, onDone }) {
  const [raw, setRaw] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  const run = async () => {
    setBusy(true);
    try {
      const res = await api.importTasks(raw);
      setResult({ ok: true, text: `Добавлено ${res.added}, пропущено повторов ${res.skipped}` });
      onDone();
    } catch {
      setResult({ ok: false, text: "Не получилось. Проверь соединение." });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="scrim" onClick={onClose}>
      <div className="sheet" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3>Импорт</h3>
          <button className="tool" onClick={onClose} aria-label="Закрыть"><X size={16} /></button>
        </div>
        <p className="hint">
          По строке на задание: <b>дата | предмет | задание</b>. Дата в виде 2026-09-15.
          Без предмета получится личное дело. Строки с # пропускаются.
        </p>
        <textarea
          className="field"
          value={raw}
          onChange={(e) => setRaw(e.target.value)}
          placeholder={"2026-09-15 | CSS 109 | Лаба 3\n2026-09-16 | забрать справку"}
        />
        <button className="save" disabled={busy || !raw.trim()} onClick={run}>
          {busy ? "Добавляем…" : "Добавить"}
        </button>
        {result && <div className={`result${result.ok ? "" : " bad"}`}>{result.text}</div>}
      </div>
    </div>
  );
}
