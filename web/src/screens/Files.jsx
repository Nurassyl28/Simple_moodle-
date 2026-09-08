import { useEffect, useState } from "react";
import { api } from "../api";

/**
 * Файлы курсов. Ссылка ведёт на наш бэкенд, а не в Moodle: токен подставляется
 * на сервере, в адресе его нет.
 */
export default function Files() {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.files().then(setRows).catch(() => setError("Moodle не отдал файлы"));
  }, []);

  if (error) return <div className="empty">{error}</div>;
  if (!rows) return <p className="loading">Собираю файлы…</p>;
  if (!rows.length) return <div className="empty">Файлов пока нет.</div>;

  const byCourse = rows.reduce((acc, row) => {
    (acc[row.course] ||= []).push(row);
    return acc;
  }, {});

  return (
    <>
      {Object.entries(byCourse).map(([course, items]) => (
        <div className="sect" key={course}>
          <div className="sect-head small"><h2>{course}</h2></div>
          <div className="card">
            {items.map((file, i) => (
              <div className="line" key={i}>
                {/* Внешняя ссылка открывается напрямую: через наш прокси её
                    качать нельзя, он подставляет токен Moodle. */}
                <a href={file.download_url || file.external_url} target="_blank" rel="noreferrer">
                  {file.name}
                </a>
                <span className="c">
                  {file.external_url ? "внешняя ссылка" : file.section}
                </span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </>
  );
}
