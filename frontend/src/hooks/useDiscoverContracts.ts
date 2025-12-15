import { useQuery } from "@tanstack/react-query";

import { discoverContracts } from "../api/client";
import { queryKeys } from "../api/queryKeys";

interface Options {
  filePath: string;
  symbolLine: number;
  enabled?: boolean;
}

/**
 * Hook to discover contracts for a symbol.
 *
 * Uses the contracts/discover API endpoint to run the multi-level
 * discovery pipeline (L1: @aegis-contract, L2: patterns, L3: LLM, L4: static).
 */
export function useDiscoverContracts(options: Options) {
  const { filePath, symbolLine, enabled = true } = options;

  return useQuery({
    queryKey: queryKeys.contracts(filePath, symbolLine),
    queryFn: () =>
      discoverContracts({
        file_path: filePath,
        symbol_line: symbolLine,
      }),
    enabled: enabled && !!filePath.trim() && symbolLine > 0,
    staleTime: 60_000,
    retry: false,
  });
}
