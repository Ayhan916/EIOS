import { useQuery } from "@tanstack/react-query";
import { getPipelineReadiness, type StepReadiness } from "@/lib/api/pipeline";

export function useReadiness() {
  return useQuery({
    queryKey: ["pipeline-readiness"],
    queryFn: getPipelineReadiness,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}

export function useStepReadiness(key: string): StepReadiness | undefined {
  const { data } = useReadiness();
  return data?.steps.find((s) => s.key === key);
}
