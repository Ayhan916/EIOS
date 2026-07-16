import { ShieldCheck } from "lucide-react";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-slate-50 via-blue-50/30 to-slate-100 px-4">
      <div className="mb-8 flex flex-col items-center gap-3">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-600 to-blue-700 shadow-lg shadow-blue-200">
          <ShieldCheck className="h-8 w-8 text-white" />
        </div>
        <div className="text-center">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            EIOS
          </h1>
          <p className="text-xs text-slate-500 font-medium tracking-wide uppercase mt-0.5">ESG Intelligence Platform</p>
        </div>
      </div>
      {children}
      <p className="mt-8 text-xs text-slate-400">© 2026 EIOS · Enterprise ESG Due Diligence</p>
    </div>
  );
}
