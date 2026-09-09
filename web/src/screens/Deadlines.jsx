import { useEffect, useState } from "react";
import { api } from "../api";
import { prettyStamp } from "../dates";

/** Ближайшие дедлайны прямо из Moodle, с переносом в личный трекер. */
export default function Deadlines() {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState("");
  const [result, setResult] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.deadlines().then(setRows).catch(() => setError("Moodle не отдал дедлайны"));
  }, []);

  const importAll = async () => {
    setBusy(true);
    try {
      const res = await api.importDeadlines();
      setResult(
        res.added || res.updated
          ? `Перенесено: ${res.added} новых, ${res.updated} обновлено`
          : "Всё уже в трекере",
      );
    } catch {
      setResult("Не получилось перенести");
    } finally {
      setBusy(false);
    }
  };

  if (error) return <div className="empty">{error}</div>;
  if (!rows) return <p className="loading">Смотрю календарь…</p>;
  if (!rows.length) {
    return (
      <div className="empty">
        Ближайших дедлайнов нет. В начале семестра это нормально.
      </div>
    );
  }

  return (
    <>
      <div className="card">
        {rows.map((row, i) => (
          <div className="line" key={i}>
            <span>
              {row.course && <b style={{ marginRight: 6 }}>{row.course}</b>}
              {row.name}
            </span>
            <span className="c">{prettyStamp(row.date)}</span>
          </div>
        ))}
      </div>
      <button className="save" disabled={busy} onClick={importAll}>
        {busy ? "Переношу…" : "Перенести в мой трекер"}
      </button>
      {result && <div className="result">{result}</div>}
    </>
  );
}
