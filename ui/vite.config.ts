import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  const API_HOST = env.VITE_API_HOST || "localhost";
  const API_PORT = env.VITE_API_PORT || "8000";

  return {
    plugins: [react()],
    server: {
      host: "0.0.0.0",
      port: 5173,
      proxy: {
        "/ws": {
          target: `ws://${API_HOST}:${API_PORT}`,
          ws: true,
        },
        "/api": {
          target: `http://${API_HOST}:${API_PORT}`,
        },
      },
    },
  };
});

