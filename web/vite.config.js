import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // В разработке фронт и gateway на разных портах. Проксируем /api, чтобы
    // браузер считал их одним источником — иначе cookie с сессией не поедет.
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
