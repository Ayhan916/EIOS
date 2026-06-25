import Link from "next/link";
import { LucideIcon } from "lucide-react";

interface EmptyStateAction {
  label: string;
  href?: string;
  onClick?: () => void;
  variant?: "primary" | "outline";
}

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  actions?: EmptyStateAction[];
  className?: string;
}

export function EmptyState({ icon: Icon, title, description, actions, className = "" }: EmptyStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center gap-3 py-16 px-6 text-center ${className}`}>
      {Icon && (
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-muted/50">
          <Icon className="h-7 w-7 text-muted-foreground/50" />
        </div>
      )}
      <div className="space-y-1">
        <p className="text-sm font-semibold text-foreground">{title}</p>
        {description && <p className="text-xs text-muted-foreground max-w-xs mx-auto leading-relaxed">{description}</p>}
      </div>
      {actions && actions.length > 0 && (
        <div className="flex items-center gap-2 mt-1">
          {actions.map((action, i) => {
            const cls = action.variant === "outline"
              ? "rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-muted transition-colors"
              : "rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors";
            if (action.href) {
              return <Link key={i} href={action.href} className={cls}>{action.label}</Link>;
            }
            return (
              <button key={i} onClick={action.onClick} className={cls}>
                {action.label}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
