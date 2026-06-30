"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useAuth } from "@/lib/auth/context";
import { useLanguage } from "@/lib/i18n/context";
import { extractErrorMessage } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";

export default function RegisterPage() {
  const { register: authRegister } = useAuth();
  const router = useRouter();
  const { t } = useLanguage();
  const [error, setError] = useState("");

  const schema = z.object({
    display_name: z.string().min(1, t("auth.nameRequired")).max(255),
    organization_name: z.string().min(1, t("auth.orgRequired")).max(255),
    email: z.string().email(t("auth.invalidEmail")),
    password: z.string().min(8, t("auth.passwordMinLength")).max(128),
  });
  type FormData = z.infer<typeof schema>;

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  async function onSubmit(data: FormData) {
    setError("");
    try {
      await authRegister(data);
      router.push("/dashboard");
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  return (
    <Card className="w-full max-w-sm shadow-lg">
      <CardHeader className="space-y-1">
        <CardTitle className="text-xl">{t("auth.signUpButton")}</CardTitle>
        <CardDescription>{t("auth.registerSubtitle")}</CardDescription>
      </CardHeader>
      <form onSubmit={handleSubmit(onSubmit)}>
        <CardContent className="space-y-4">
          {error && (
            <div className="rounded-md bg-red-50 px-4 py-3 text-sm text-red-700 border border-red-200">
              {error}
            </div>
          )}
          <div className="space-y-2">
            <Label htmlFor="display_name">{t("auth.displayName")}</Label>
            <Input
              id="display_name"
              placeholder="Max Mustermann"
              autoComplete="name"
              {...register("display_name")}
            />
            {errors.display_name && (
              <p className="text-xs text-destructive">
                {errors.display_name.message}
              </p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="organization_name">{t("auth.organizationName")}</Label>
            <Input
              id="organization_name"
              placeholder="Mustermann GmbH"
              {...register("organization_name")}
            />
            {errors.organization_name && (
              <p className="text-xs text-destructive">
                {errors.organization_name.message}
              </p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="email">{t("auth.email")}</Label>
            <Input
              id="email"
              type="email"
              placeholder="max@mustermann.de"
              autoComplete="email"
              {...register("email")}
            />
            {errors.email && (
              <p className="text-xs text-destructive">{errors.email.message}</p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">{t("auth.password")}</Label>
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
              placeholder={t("auth.passwordMinLength")}
              {...register("password")}
            />
            {errors.password && (
              <p className="text-xs text-destructive">
                {errors.password.message}
              </p>
            )}
          </div>
        </CardContent>
        <CardFooter className="flex flex-col gap-3">
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? (
              <Spinner size="sm" className="text-white" />
            ) : (
              t("auth.signUpButton")
            )}
          </Button>
          <p className="text-center text-sm text-muted-foreground">
            {t("auth.hasAccount")}{" "}
            <Link
              href="/login"
              className="font-medium text-primary underline-offset-4 hover:underline"
            >
              {t("auth.signUpLink")}
            </Link>
          </p>
        </CardFooter>
      </form>
    </Card>
  );
}
