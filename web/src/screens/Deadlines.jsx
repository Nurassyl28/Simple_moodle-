import { useEffect, useState } from "react";
import { api } from "../api";
import { prettyStamp } from "../dates";

/** Ближайшие дедлайны прямо из Moodle, без записи в трекер. */
export default function Deadlines() {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState("");
  const [imported, setImported] = useState("");

  useEffect(() => {
    api.deadlines().then(setRows).catch(() => setError("Moodle не отдал дедлайны"));
  }, []);

  const importAll = async () => {
    try {
      const res = await api.importDeadlines();
      setImported(`Добавлено ${res.added}, обновлено ${res.updated}`);
    } catch {
      setImported("Не получилось перенести");
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
      <button className="save" onClick={importAll}>Перенести в мой трекер</button>
      {imported && <div className="result">{imported}</div>}
    </>
  );
}
