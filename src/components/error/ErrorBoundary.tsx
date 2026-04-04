"use client";

import { Component, type ErrorInfo, type ReactNode } from "react";

type Props = {
  children: ReactNode;
};

type State = {
  hasError: boolean;
};

export default class ErrorBoundary extends Component<Props, State> {
  public state: State = { hasError: false };

  public static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Keeps runtime failures visible during development without crashing whole shell.
    // eslint-disable-next-line no-console
    console.error("Workspace render error", error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="rounded-md border border-red-300/40 bg-red-300/10 p-3 text-sm text-red-100">
          Workspace UI encountered an error. Refresh the page or retry the run.
        </div>
      );
    }

    return this.props.children;
  }
}
