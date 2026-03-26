import React from "react";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null, info: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    // Also print to console for devtools
    console.error("UI crashed:", error, info);
    this.setState({ info });
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{
          minHeight: "100vh",
          display: "grid",
          placeItems: "center",
          padding: 24,
          background: "#08101b",
          color: "#e7ecf6",
          fontFamily: "\"Segoe UI\", system-ui, sans-serif",
        }}>
          <div style={{
            width: "min(520px, 100%)",
            border: "1px solid rgba(154,169,193,0.18)",
            borderRadius: 18,
            background: "linear-gradient(180deg, rgba(12,20,33,0.92), rgba(18,28,44,0.92))",
            padding: 28,
          }}>
            <div style={{ color: "#9da9bf", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.14em", marginBottom: 6 }}>
              Operational Shell
            </div>
            <h2 style={{ marginTop: 0, marginBottom: 8 }}>Shell unavailable</h2>
            <p style={{ margin: 0, color: "#9da9bf", lineHeight: 1.5 }}>
              The frontend encountered an unexpected error and could not finish rendering the command shell.
            </p>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
