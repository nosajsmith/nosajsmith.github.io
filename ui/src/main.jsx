import React from "react";
import ReactDOM from "react-dom/client";
// Canonical live shell entry. Keep `App.tsx` as the mounted app root.
import App from "./App.tsx";
import ErrorBoundary from "./components/ErrorBoundary.jsx";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);
