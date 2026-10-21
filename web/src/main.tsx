import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles.css";
import "./site/site.css";

// No StrictMode: its development-only double mount tears down drei's <Html> overlays
// (thought bubbles, name tag) and would start the demo director twice.
createRoot(document.getElementById("root")!).render(<App />);
