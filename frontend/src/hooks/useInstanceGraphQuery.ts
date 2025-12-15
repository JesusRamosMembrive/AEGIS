import { useQuery } from "@tanstack/react-query";

import { getInstanceGraph } from "../api/client";
import { queryKeys } from "../api/queryKeys";

interface Options {
  projectPath: string;
  enabled?: boolean;
}

export function useInstanceGraphQuery(options: Options) {
  const { projectPath, enabled = true } = options;

  return useQuery({
    queryKey: queryKeys.instanceGraph(projectPath),
    queryFn: () => getInstanceGraph(projectPath),
    enabled: enabled && !!projectPath.trim(),
    staleTime: 60_000,
  });
}
