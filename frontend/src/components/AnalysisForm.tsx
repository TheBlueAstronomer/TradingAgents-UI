"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useMemo, useRef, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { ApiClientError, createAnalysis } from "@/lib/api";
import type {
  AnalystOption,
  AnalysisCreate,
  AnalysisSummary,
  ProviderOption,
} from "@/lib/types";

type FormValues = AnalysisCreate & {
  quick_custom_model: string;
  deep_custom_model: string;
};

const baseSchema = z.object({
  ticker: z
    .string()
    .trim()
    .regex(
      /^[A-Za-z0-9^][A-Za-z0-9.^=_-]{0,31}$/,
      "Enter a valid market symbol",
    ),
  analysis_date: z.string().min(1, "Select a date"),
  analysts: z
    .array(z.enum(["market", "social", "news", "fundamentals"]))
    .min(1, "Select at least one analyst"),
  llm_provider: z.string().min(1, "Choose a provider"),
  quick_think_llm: z.string().min(1, "Choose a quick model"),
  deep_think_llm: z.string().min(1, "Choose a deep model"),
  quick_custom_model: z.string(),
  deep_custom_model: z.string(),
  research_depth: z.coerce.number().min(1, "Choose a research depth").max(5),
  backend_url: z.string(),
});

function hasCustomOption(models: ProviderOption["quick_models"]) {
  return models.some((model) => model.value === "custom");
}

function isRealCustomModel(value: string) {
  return value.length > 0 && value === value.trim() && value.length <= 128;
}

export function AnalysisForm({
  providers,
  analysts,
  onCreated,
}: {
  providers: ProviderOption[];
  analysts: AnalystOption[];
  onCreated?: (run: AnalysisSummary) => void;
}) {
  const configured = providers.length > 0 && analysts.length > 0;
  const formSchema = useMemo(
    () =>
      baseSchema.superRefine((values, context) => {
        const provider = providers.find(
          (candidate) => candidate.id === values.llm_provider,
        );

        if (!provider) {
          context.addIssue({
            code: z.ZodIssueCode.custom,
            path: ["llm_provider"],
            message: "Choose a valid provider",
          });
          return;
        }

        const validateModel = (
          field: "quick_think_llm" | "deep_think_llm",
          customField: "quick_custom_model" | "deep_custom_model",
          models: ProviderOption["quick_models"],
          label: string,
        ) => {
          const selected = values[field];
          const known = new Set(models.map((model) => model.value));

          if (selected === "custom") {
            if (!hasCustomOption(models)) {
              context.addIssue({
                code: z.ZodIssueCode.custom,
                path: [field],
                message: `Choose a valid ${label} model`,
              });
            }
            if (!isRealCustomModel(values[customField])) {
              context.addIssue({
                code: z.ZodIssueCode.custom,
                path: [customField],
                message: "Enter a trimmed model ID of 128 characters or fewer",
              });
            }
            return;
          }

          if (!known.has(selected)) {
            context.addIssue({
              code: z.ZodIssueCode.custom,
              path: [field],
              message: `Choose a valid ${label} model`,
            });
          }
        };

        validateModel(
          "quick_think_llm",
          "quick_custom_model",
          provider.quick_models,
          "quick",
        );
        validateModel(
          "deep_think_llm",
          "deep_custom_model",
          provider.deep_models,
          "deep",
        );

        if (provider.requires_backend_url) {
          const result = z.string().url().safeParse(values.backend_url.trim());
          if (!result.success) {
            context.addIssue({
              code: z.ZodIssueCode.custom,
              path: ["backend_url"],
              message: "Enter a complete backend URL",
            });
          }
        }
      }),
    [providers],
  );
  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      ticker: "",
      analysis_date: new Date().toISOString().slice(0, 10),
      analysts: [],
      llm_provider: "",
      quick_think_llm: "",
      deep_think_llm: "",
      quick_custom_model: "",
      deep_custom_model: "",
      research_depth: 1,
      backend_url: "",
    },
  });
  const { getValues, reset, setValue } = form;
  const selectedProviderId = useWatch({
    control: form.control,
    name: "llm_provider",
  });
  const quickModel = useWatch({
    control: form.control,
    name: "quick_think_llm",
  });
  const deepModel = useWatch({
    control: form.control,
    name: "deep_think_llm",
  });
  const provider = providers.find((item) => item.id === selectedProviderId);
  const initialized = useRef(false);
  const [serverError, setServerError] = useState("");

  useEffect(() => {
    if (!configured || initialized.current) return;

    const current = getValues();
    const currentProvider = providers.find(
      (item) => item.id === current.llm_provider,
    );
    const selected = currentProvider ?? providers[0];
    const quickStillValid = selected.quick_models.some(
      (model) => model.value === current.quick_think_llm,
    );
    const deepStillValid = selected.deep_models.some(
      (model) => model.value === current.deep_think_llm,
    );

    reset({
      ...current,
      analysts:
        current.analysts.length > 0
          ? current.analysts
          : analysts
              .filter((item) => item.selected_by_default)
              .map((item) => item.id),
      llm_provider: selected.id,
      quick_think_llm: quickStillValid
        ? current.quick_think_llm
        : selected.default_quick_model,
      deep_think_llm: deepStillValid
        ? current.deep_think_llm
        : selected.default_deep_model,
      backend_url: selected.requires_backend_url ? current.backend_url : "",
    });
    initialized.current = true;
  }, [analysts, configured, getValues, providers, reset]);

  const changeProvider = (nextProviderId: string) => {
    const nextProvider = providers.find((item) => item.id === nextProviderId);
    setValue("llm_provider", nextProviderId, {
      shouldDirty: true,
      shouldValidate: true,
    });
    if (!nextProvider) return;

    setValue("quick_think_llm", nextProvider.default_quick_model, {
      shouldDirty: true,
      shouldValidate: true,
    });
    setValue("deep_think_llm", nextProvider.default_deep_model, {
      shouldDirty: true,
      shouldValidate: true,
    });
    setValue("quick_custom_model", "", { shouldDirty: true });
    setValue("deep_custom_model", "", { shouldDirty: true });
    setValue("backend_url", "", { shouldDirty: true });
  };

  const error = (message?: string) =>
    message && <small role="alert">{message}</small>;
  const showQuickCustom =
    quickModel === "custom" && hasCustomOption(provider?.quick_models ?? []);
  const showDeepCustom =
    deepModel === "custom" && hasCustomOption(provider?.deep_models ?? []);

  return (
    <section className="cover-sheet" aria-labelledby="new-docket">
      <header>
        <span className="folio">New research docket</span>
        <h1 id="new-docket">Open an analysis</h1>
        <p>
          Set the instrument and review team. Your local backend owns provider
          credentials.
        </p>
      </header>
      <form
        noValidate
        onSubmit={form.handleSubmit(async (values) => {
          setServerError("");
          const activeProvider = providers.find(
            (item) => item.id === values.llm_provider,
          );
          if (!activeProvider) return;

          const request: AnalysisCreate = {
            ticker: values.ticker.toUpperCase(),
            analysis_date: values.analysis_date,
            analysts: values.analysts,
            llm_provider: values.llm_provider,
            quick_think_llm:
              values.quick_think_llm === "custom"
                ? values.quick_custom_model.trim()
                : values.quick_think_llm,
            deep_think_llm:
              values.deep_think_llm === "custom"
                ? values.deep_custom_model.trim()
                : values.deep_think_llm,
            research_depth: values.research_depth,
            ...(activeProvider.requires_backend_url
              ? { backend_url: values.backend_url?.trim() ?? "" }
              : {}),
          };

          try {
            onCreated?.(await createAnalysis(request));
          } catch (exception) {
            setServerError(
              exception instanceof ApiClientError
                ? exception.message
                : "Unable to open the docket.",
            );
          }
        })}
      >
        <div className="form-grid">
          <div>
            <Label htmlFor="ticker">Ticker</Label>
            <Input
              id="ticker"
              placeholder="AAPL"
              {...form.register("ticker")}
            />
            {error(form.formState.errors.ticker?.message)}
          </div>
          <div>
            <Label htmlFor="date">Analysis date</Label>
            <Input
              id="date"
              type="date"
              max={new Date().toISOString().slice(0, 10)}
              {...form.register("analysis_date")}
            />
            {error(form.formState.errors.analysis_date?.message)}
          </div>
        </div>
        <fieldset>
          <legend>Evidence team</legend>
          {analysts.map((analyst) => (
            <Label className="checkline" key={analyst.id}>
              <input
                type="checkbox"
                value={analyst.id}
                {...form.register("analysts")}
              />
              <span>
                <b>{analyst.label}</b>
                <small className="muted-copy">{analyst.description}</small>
              </span>
            </Label>
          ))}
          {error(form.formState.errors.analysts?.message)}
        </fieldset>
        <div>
          <Label htmlFor="provider">Provider</Label>
          <Select
            id="provider"
            disabled={!configured}
            value={selectedProviderId}
            onChange={(event) => changeProvider(event.target.value)}
          >
            <option value="">
              {configured ? "Choose provider" : "Loading provider options…"}
            </option>
            {providers.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </Select>
          {error(form.formState.errors.llm_provider?.message)}
        </div>
        <div className="form-grid">
          <div>
            <Label htmlFor="quick">Quick model</Label>
            <Select
              id="quick"
              disabled={!configured || !provider}
              value={quickModel}
              onChange={(event) =>
                setValue("quick_think_llm", event.target.value, {
                  shouldDirty: true,
                  shouldValidate: true,
                })
              }
            >
              <option value="">Choose model</option>
              {provider?.quick_models.map((model) => (
                <option key={model.value} value={model.value}>
                  {model.label}
                </option>
              ))}
            </Select>
            {showQuickCustom && (
              <>
                <Label htmlFor="quick-custom">Quick custom model</Label>
                <Input
                  id="quick-custom"
                  required
                  maxLength={128}
                  placeholder="Provider model ID"
                  {...form.register("quick_custom_model")}
                />
                {error(form.formState.errors.quick_custom_model?.message)}
              </>
            )}
            {error(form.formState.errors.quick_think_llm?.message)}
          </div>
          <div>
            <Label htmlFor="deep">Deep model</Label>
            <Select
              id="deep"
              disabled={!configured || !provider}
              value={deepModel}
              onChange={(event) =>
                setValue("deep_think_llm", event.target.value, {
                  shouldDirty: true,
                  shouldValidate: true,
                })
              }
            >
              <option value="">Choose model</option>
              {provider?.deep_models.map((model) => (
                <option key={model.value} value={model.value}>
                  {model.label}
                </option>
              ))}
            </Select>
            {showDeepCustom && (
              <>
                <Label htmlFor="deep-custom">Deep custom model</Label>
                <Input
                  id="deep-custom"
                  required
                  maxLength={128}
                  placeholder="Provider model ID"
                  {...form.register("deep_custom_model")}
                />
                {error(form.formState.errors.deep_custom_model?.message)}
              </>
            )}
            {error(form.formState.errors.deep_think_llm?.message)}
          </div>
        </div>
        {provider?.requires_backend_url && (
          <div>
            <Label htmlFor="backend">Compatible backend URL</Label>
            <Input
              id="backend"
              type="url"
              required
              {...form.register("backend_url")}
            />
            {error(form.formState.errors.backend_url?.message)}
          </div>
        )}
        <div>
          <Label htmlFor="depth">Research depth</Label>
          <Select
            id="depth"
            disabled={!configured}
            {...form.register("research_depth", { valueAsNumber: true })}
          >
            {[1, 2, 3, 4, 5].map((depth) => (
              <option key={depth} value={depth}>
                {depth} round{depth > 1 ? "s" : ""}
              </option>
            ))}
          </Select>
          {error(form.formState.errors.research_depth?.message)}
        </div>
        {serverError && (
          <p className="error-note" role="alert">
            {serverError}
          </p>
        )}
        <Button
          type="submit"
          disabled={!configured || form.formState.isSubmitting}
          aria-busy={form.formState.isSubmitting}
        >
          {form.formState.isSubmitting
            ? "Opening docket…"
            : configured
              ? "Start analysis"
              : "Loading configuration…"}
        </Button>
      </form>
    </section>
  );
}
