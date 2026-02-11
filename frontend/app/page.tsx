"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import axios from "axios";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

/* ─── Types ──────────────────────────────────────────────────────────────── */
interface CandidateResult {
  name: string;
  email?: string | null;
  phone?: string | null;
  github?: string | null;
  score: number;
  classification: "Excellent" | "Strong" | "Partial" | "Weak";
  summary: string;
  matched_keywords?: string[];
  jd_keywords?: string[];
  match_ratio?: number;
}
type ServerStatus = "checking" | "online" | "offline";

/* ─── Icons (inline SVGs to avoid extra deps) ────────────────────────────── */
const Icons = {
  upload: (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  ),
  file: (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" /><polyline points="14 2 14 8 20 8" />
    </svg>
  ),
  loader: (
    <svg className="animate-spin" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
  ),
  alertCircle: (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  ),
  check: (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  ),
  x: (
    <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  ),
  sparkles: (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
    </svg>
  ),
  mail: (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect width="20" height="16" x="2" y="4" rx="2" /><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
    </svg>
  ),
  phone: (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
    </svg>
  ),
  github: (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0 1 12 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z" />
    </svg>
  ),
};

/* ─── Component ──────────────────────────────────────────────────────────── */
export default function Home() {
  const [jd, setJd] = useState("");
  const [files, setFiles] = useState<FileList | null>(null);
  const [progress, setProgress] = useState(0);
  const [total, setTotal] = useState(0);
  const [processed, setProcessed] = useState(0);
  const [results, setResults] = useState<CandidateResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [serverStatus, setServerStatus] = useState<ServerStatus>("checking");
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  /* ── Server health ─────────────────────────────────────────────────── */
  useEffect(() => {
    const check = async () => {
      try {
        const res = await axios.get(`${API_BASE}/`, { timeout: 3000 });
        setServerStatus(res.status === 200 ? "online" : "offline");
      } catch {
        setServerStatus("offline");
      }
    };
    check();
    const id = setInterval(check, 30_000);
    return () => clearInterval(id);
  }, []);

  /* ── Start job ─────────────────────────────────────────────────────── */
  const startJob = async () => {
    if (!files || !jd.trim()) {
      setError("Please provide a job description and upload at least one resume.");
      return;
    }
    setLoading(true);
    setError(null);
    setResults([]);
    setProgress(0);

    const formData = new FormData();
    formData.append("jd", jd);
    for (let i = 0; i < files.length; i++) formData.append("files", files[i]);

    try {
      const res = await axios.post(`${API_BASE}/start-job`, formData, {
        timeout: 300_000, // 5min timeout for long sync processing
        headers: { "Content-Type": "multipart/form-data" },
      });
      const data = res.data;
      
      setTotal(data.total || 0);
      setProcessed(data.processed || 0);
      setResults(data.candidates || []);
      
      if (data.status === "failed") {
        setError("Processing failed. Please try again.");
      }
      
      // Optimization: jump to 100% since we are done
      setProgress(100);
      setLoading(false);

    } catch (err) {
      setLoading(false);
      if (axios.isAxiosError(err)) {
        if (err.code === "ECONNREFUSED" || err.code === "ERR_NETWORK")
          setError("Cannot connect to server. Is the backend running?");
        else if (err.response?.status === 400)
          setError(err.response.data?.detail || "Invalid request.");
        else if (err.code === "ECONNABORTED")
          setError("Request timed out. The server took too long to respond.");
        else setError(err.response?.data?.detail || "Something went wrong.");
      } else {
        setError("An unexpected error occurred.");
      }
    }
  };

  /* ── Drag & drop ───────────────────────────────────────────────────── */
  const onDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(e.type === "dragenter" || e.type === "dragover");
  };
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files?.length) setFiles(e.dataTransfer.files);
  };

  /* ── Helpers ───────────────────────────────────────────────────────── */
  const classificationBadge = (c: string) => {
    switch (c) {
      case "Excellent": return "bg-success/10 text-success border-success/20 hover:bg-success/15";
      case "Strong":    return "bg-info/10 text-info border-info/20 hover:bg-info/15";
      case "Partial":   return "bg-warning/10 text-warning border-warning/20 hover:bg-warning/15";
      default:          return "bg-destructive/10 text-destructive border-destructive/20 hover:bg-destructive/15";
    }
  };
  const scoreColor = (s: number) => {
    if (s >= 80) return "text-success";
    if (s >= 60) return "text-info";
    if (s >= 40) return "text-warning";
    return "text-destructive";
  };

  /* ─── Render ───────────────────────────────────────────────────────── */
  return (
    <div className="min-h-screen bg-background">
      {/* ── Header ─────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="mx-auto flex h-14 max-w-3xl items-center justify-between px-6">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              {Icons.sparkles}
            </div>
            <div className="leading-tight">
              <p className="text-sm font-semibold">Resume Analyzer</p>
              <p className="text-[11px] text-muted-foreground">AI-powered candidate screening</p>
            </div>
          </div>
          <Badge
            variant="outline"
            className={`gap-1.5 text-[11px] ${
              serverStatus === "online"
                ? "border-success/30 text-success"
                : serverStatus === "offline"
                ? "border-destructive/30 text-destructive"
                : "text-muted-foreground"
            }`}
          >
            <span className={`inline-block h-1.5 w-1.5 rounded-full ${
              serverStatus === "online"
                ? "bg-success"
                : serverStatus === "offline"
                ? "bg-destructive"
                : "bg-muted-foreground animate-pulse"
            }`} />
            {serverStatus === "online" ? "Online" : serverStatus === "offline" ? "Offline" : "Checking…"}
          </Badge>
        </div>
      </header>

      {/* ── Main ───────────────────────────────────────────────────── */}
      <main className="mx-auto max-w-3xl space-y-5 px-6 py-8">

        {/* ── Job Description ──────────────────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Job Description</CardTitle>
            <CardDescription>
              Describe the role, required skills, and qualifications
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Textarea
              rows={5}
              placeholder="e.g., We're looking for a senior Python developer with experience in FastAPI, PostgreSQL, and machine learning…"
              value={jd}
              onChange={(e) => setJd(e.target.value)}
              className="resize-none text-sm"
            />
            <p className="mt-2 text-xs text-muted-foreground">
              {jd.length > 0 ? `${jd.length} characters` : "Paste or type the full job requirements"}
            </p>
          </CardContent>
        </Card>

        {/* ── File Upload ──────────────────────────────────────────── */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Upload Resumes</CardTitle>
            <CardDescription>
              PDF, DOC, or DOCX files — up to 20 at a time
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div
              className={`
                group relative flex cursor-pointer flex-col items-center justify-center
                rounded-lg border-2 border-dashed p-8 transition-colors
                ${dragActive
                  ? "border-primary bg-primary/5"
                  : "border-muted-foreground/20 hover:border-muted-foreground/40 hover:bg-muted/50"
                }
              `}
              onDragEnter={onDrag}
              onDragOver={onDrag}
              onDragLeave={onDrag}
              onDrop={onDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,.doc,.docx"
                className="hidden"
                onChange={(e) => setFiles(e.target.files)}
              />
              <div className="mb-3 rounded-full bg-muted p-3 text-muted-foreground group-hover:text-foreground transition-colors">
                {Icons.upload}
              </div>
              {files ? (
                <p className="text-sm font-medium">
                  {files.length} file{files.length !== 1 && "s"} selected
                </p>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Drop files here or{" "}
                  <span className="font-medium text-foreground underline underline-offset-4">browse</span>
                </p>
              )}
              <p className="mt-1 text-xs text-muted-foreground">PDF, DOC, DOCX</p>
            </div>

            {files && files.length > 0 && (
              <div className="flex flex-wrap gap-1.5 animate-fade-up">
                {Array.from(files).map((f, i) => (
                  <Badge key={i} variant="secondary" className="gap-1 text-xs font-normal">
                    {Icons.file}
                    {f.name.length > 28 ? f.name.slice(0, 25) + "…" : f.name}
                  </Badge>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* ── Warnings / Errors ────────────────────────────────────── */}
        {serverStatus === "offline" && (
          <Alert className="animate-fade-up border-warning/30 bg-warning-muted text-warning">
            <span>{Icons.alertCircle}</span>
            <div>
              <AlertTitle className="text-warning">Server Unreachable</AlertTitle>
              <AlertDescription className="text-warning/80">
                Resume analysis will use basic keyword matching. Start the backend for AI-powered results.
              </AlertDescription>
            </div>
          </Alert>
        )}

        {error && (
          <Alert variant="destructive" className="animate-fade-up">
            <span>{Icons.alertCircle}</span>
            <div>
              <AlertTitle>Error</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </div>
          </Alert>
        )}

        {/* ── Start Button ─────────────────────────────────────────── */}
        <Button
          onClick={startJob}
          disabled={loading || !jd.trim() || !files}
          className="w-full"
          size="lg"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              {Icons.loader}
              Analyzing…
            </span>
          ) : (
            "Start Analysis"
          )}
        </Button>

        {/* ── Progress ─────────────────────────────────────────────── */}
        {loading && (
          <Card className="animate-fade-up">
            <CardContent className="pt-6 space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium">Processing resumes</p>
                <p className="text-xs tabular-nums text-muted-foreground">
                  Please wait, this may take a minute...
                </p>
              </div>
              <Progress value={progress > 0 ? progress : 5} className="h-2 animate-pulse" />
              <p className="text-xs text-muted-foreground">
                Evaluating candidates against job requirements...
              </p>
            </CardContent>
          </Card>
        )}

        {/* ── Results ──────────────────────────────────────────────── */}
        {results.length > 0 && (
          <section className="space-y-4 animate-fade-up">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold tracking-tight">Results</h2>
              <Badge variant="secondary" className="text-xs">
                {results.length} candidate{results.length !== 1 && "s"}
              </Badge>
            </div>

            <div className="space-y-3">
              {results.map((r, i) => (
                <Card
                  key={i}
                  className="animate-slide-in overflow-hidden transition-shadow hover:shadow-md"
                  style={{ animationDelay: `${i * 50}ms` }}
                >
                  <CardContent className="pt-6">
                    {/* Header row */}
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-center gap-3 min-w-0">
                        {/* Avatar */}
                        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-muted text-sm font-semibold">
                          {r.name?.charAt(0)?.toUpperCase() || "?"}
                        </div>
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold">{r.name}</p>
                          <div className="mt-1 flex items-center gap-2">
                            <Badge
                              variant="outline"
                              className={`text-[10px] uppercase tracking-wider ${classificationBadge(r.classification)}`}
                            >
                              {r.classification}
                            </Badge>
                          </div>
                        </div>
                      </div>
                      {/* Score */}
                      <div className="shrink-0 text-right">
                        <span className={`text-2xl font-bold tabular-nums ${scoreColor(r.score)}`}>
                          {r.score}
                        </span>
                        <span className={`text-sm ${scoreColor(r.score)}`}>/100</span>
                      </div>
                    </div>

                    {/* Summary */}
                    {r.summary && (
                      <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                        {r.summary}
                      </p>
                    )}

                    {/* Contact info */}
                    {(r.email || r.phone || r.github) && (
                      <div className="mt-3 flex flex-wrap items-center gap-2">
                        {r.email && (
                          <a
                            href={`mailto:${r.email}`}
                            className="inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                          >
                            {Icons.mail}
                            {r.email}
                          </a>
                        )}
                        {r.phone && (
                          <a
                            href={`tel:${r.phone.replace(/[^+\d]/g, '')}`}
                            className="inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                          >
                            {Icons.phone}
                            {r.phone}
                          </a>
                        )}
                        {r.github && (
                          <a
                            href={r.github}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                          >
                            {Icons.github}
                            {r.github.replace('https://github.com/', '@')}
                          </a>
                        )}
                      </div>
                    )}

                    {/* Skill match */}
                    {(r.matched_keywords?.length || r.jd_keywords?.length) ? (
                      <>
                        <Separator className="my-4" />
                        <div className="space-y-3">
                          <div className="flex items-center justify-between">
                            <p className="text-xs font-medium">Skill Match</p>
                            {r.match_ratio !== undefined && (
                              <span className="text-xs tabular-nums text-muted-foreground">
                                {Math.round(r.match_ratio * 100)}% overlap
                              </span>
                            )}
                          </div>

                          {r.match_ratio !== undefined && (
                            <Progress
                              value={Math.round(r.match_ratio * 100)}
                              className="h-1.5"
                            />
                          )}

                          {r.matched_keywords && r.matched_keywords.length > 0 && (
                            <div className="flex flex-wrap gap-1.5">
                              {r.matched_keywords.slice(0, 8).map((kw, idx) => (
                                <Badge
                                  key={idx}
                                  variant="outline"
                                  className="gap-1 bg-success/10 text-success border-success/20 text-[11px] font-normal"
                                >
                                  {Icons.check}
                                  {kw}
                                </Badge>
                              ))}
                              {r.matched_keywords.length > 8 && (
                                <Badge variant="secondary" className="text-[11px] font-normal">
                                  +{r.matched_keywords.length - 8} more
                                </Badge>
                              )}
                            </div>
                          )}

                          {r.jd_keywords && r.jd_keywords.length > 0 && (
                            <div className="flex flex-wrap gap-1.5">
                              {r.jd_keywords.slice(0, 6).map((kw, idx) => {
                                const matched = r.matched_keywords?.includes(kw);
                                return (
                                  <Badge
                                    key={idx}
                                    variant="outline"
                                    className={`text-[11px] font-normal ${
                                      matched
                                        ? "bg-info/10 text-info border-info/20"
                                        : "text-muted-foreground"
                                    }`}
                                  >
                                    {kw}
                                    {!matched && <span className="ml-0.5 text-destructive">{Icons.x}</span>}
                                  </Badge>
                                );
                              })}
                            </div>
                          )}
                        </div>
                      </>
                    ) : null}
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
