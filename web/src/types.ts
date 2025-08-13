export type JobProgress = { iteration: number; pct: number; digest: string };

export type LLJobResult = {
  p: number;
  is_prime: boolean;
  iterations: number;
  ns_elapsed: number;
  final_residue_is_zero: boolean;
  engine_info: string;
};

export type JobStatus = {
  id: string;
  p: number;
  status: "queued" | "running" | "done" | "error";
  result?: LLJobResult | null;
  error?: string | null;
};

export type DigitsCreateResp = {
  id: string;
  p: number;
  estimated_digits: number;
};

export type DigitsArtifact = {
  job_id: string;
  filename: string;
  path: string;
  digits: number;
  size_bytes: number;
  sha256: string;
};

export type DigitsJob = {
  id: string;
  kind: "digits";
  p: number;
  status: "queued" | "running" | "done" | "error";
  created_at: number;
  started_at?: number | null;
  finished_at?: number | null;
  error?: string | null;
  engine_info?: string | null;
  artifact?: DigitsArtifact | null;
};

export type BlockSummary = {
  id: number;
  start: number;
  end_excl: number;
  label: string;
  candidate_count: number;
  tested_count: number;
  verified_count: number;
  status: string;
};

export type BlockDetail = {
  block: {
    id: number;
    start: number;
    end_excl: number;
    candidate_count: number;
    tested_count: number;
    verified_count: number;
    status: string;
  };
  exponents: Array<{
    p: number;
    status: "queued" | "running" | "done" | "error";
    is_prime: 0 | 1 | null;
    ns_elapsed: number | null;
    engine_info: string | null;
  }>;
};

export type BlockWsMsg = {
  block_id: number;
  last_p?: number;
  tested: number;
  total: number;
  done?: boolean;
  p?: number;
  pct?: number;
};

export type PrimeRow = {
  p: number;
  block_id: number;
  digits: number;
  finished_at: number | null;
  engine_info: string | null;
  ns_elapsed: number | null;
};
