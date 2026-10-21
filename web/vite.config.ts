import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "./", // relative URLs: works at any path (e.g. username.github.io/ada/)
  plugins: [react()],
  server: { port: 5180, strictPort: true },
});
