import { Component, ErrorInfo, ReactNode } from "react";

type ErrorBoundaryProps = {
  children: ReactNode;
  title?: string;
};

type ErrorBoundaryState = {
  hasError: boolean;
  message: string;
};

export default class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, message: "" };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      message: error?.message || "发生了未知前端错误。",
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("EduInsight frontend error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="panel border-rose-200 bg-rose-50 p-6 text-rose-700">
          <h3 className="text-base font-semibold">{this.props.title ?? "页面渲染失败"}</h3>
          <p className="mt-3 text-sm leading-6">
            前端组件在渲染时发生错误。当前不是浏览器遮住了页面，而是页面内部抛出了异常。
          </p>
          <pre className="mt-4 overflow-x-auto rounded-lg bg-white px-4 py-3 text-xs leading-6 text-rose-700">
            {this.state.message}
          </pre>
        </div>
      );
    }

    return this.props.children;
  }
}