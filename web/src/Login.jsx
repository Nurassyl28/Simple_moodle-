import { useState } from "react";
import { api } from "./api";

/**
 * Экран входа. По SECURITY.md он обязан честно сказать студенту, что происходит
 * с его паролем — этот текст не украшение, а требование.
 */
export default function Login({ onDone }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const me = await api.login(username.trim(), password);
      setPassword("");
      onDone(me);
    } catch (err) {
      setError(
        err.status === 401
          ? "Неверный логин или пароль"
          : "Moodle сейчас не отвечает. Попробуй позже.",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="login" onSubmit={submit}>
      <h1>SDU Hub</h1>
      <p className="hint">
        Войди логином от Moodle. Мы войдём в Moodle от твоего имени, чтобы показать
        твои курсы, оценки и дедлайны. <b>Пароль нигде не сохраняется</b> — он нужен
        один раз, чтобы получить доступ.
      </p>

      <input
        className="field"
        placeholder="Логин Moodle"
        autoComplete="username"
        autoCapitalize="none"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
      />
      <input
        className="field"
        type="password"
        placeholder="Пароль"
        autoComplete="current-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />

      <button className="save" disabled={busy || !username.trim() || !password}>
        {busy ? "Входим…" : "Войти"}
      </button>

      {error && <div className="err">{error}</div>}
    </form>
  );
}
