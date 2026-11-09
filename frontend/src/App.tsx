import { useEffect, useState } from "react";

type Finding = {
  check: string;
  severity: string;
  location: string;
  explanation: string;
};

type TaskSummary = {
  id: string;
  title: string;
  requirements: number;
  requirement_coverage: number;
  mutation_score: number;
  finding_count: number;
};

type TaskDetail = {
  id: string;
  title: string;
  requirements: number;
  requirement_coverage: number;
  mutation_score: number;
  findings: Finding[];
};

export function App() {
  const [tasks, setTasks] = useState<TaskSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<TaskDetail | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/tasks")
      .then((response) => readJson<TaskSummary[]>(response))
      .then((rows) => {
        if (!cancelled) {
          setTasks(rows);
        }
      })
      .catch((reason: unknown) => {
        if (!cancelled) {
          setError(message(reason));
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (selectedId === null) {
      return;
    }
    let cancelled = false;
    setDetail(null);
    fetch(`/api/tasks/${selectedId}`)
      .then((response) => readJson<TaskDetail>(response))
      .then((task) => {
        if (!cancelled) {
          setDetail(task);
        }
      })
      .catch((reason: unknown) => {
        if (!cancelled) {
          setError(message(reason));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  return (
    <main>
      <header>
        <p className="eyebrow">Invented sample tasks</p>
        <h1>TaskAuditor</h1>
      </header>
      {error !== null ? <p className="error">{error}</p> : null}
      {tasks === null && error === null ? <p>Loading stored tasks.</p> : null}
      {tasks !== null && tasks.length === 0 ? <EmptyState /> : null}
      {tasks !== null && tasks.length > 0 ? (
        <div className="layout">
          <section>
            <h2>Sample tasks</h2>
            <ul className="task-list">
              {tasks.map((task) => (
                <li key={task.id}>
                  <button
                    type="button"
                    aria-pressed={task.id === selectedId}
                    onClick={() => {
                      setSelectedId(task.id);
                    }}
                  >
                    <span className="task-id">{task.id}</span>
                    <span className="task-title">{task.title}</span>
                    <span className="task-count">
                      {task.finding_count === 0
                        ? "No findings"
                        : `${task.finding_count} finding${task.finding_count === 1 ? "" : "s"}`}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
          <TaskPanel selected={selectedId !== null} detail={detail} />
        </div>
      ) : null}
    </main>
  );
}

function EmptyState() {
  return (
    <section className="empty">
      <h2>No tasks stored</h2>
      <p>
        Audit a sample task and store its JSON report. This page lists those
        results and their findings.
      </p>
    </section>
  );
}

function TaskPanel({
  selected,
  detail,
}: {
  selected: boolean;
  detail: TaskDetail | null;
}) {
  if (!selected) {
    return (
      <section className="detail">
        <h2>Findings</h2>
        <p>Select a task from the list.</p>
      </section>
    );
  }
  if (detail === null) {
    return (
      <section className="detail">
        <h2>Findings</h2>
        <p>Loading findings.</p>
      </section>
    );
  }
  return (
    <section className="detail">
      <h2>{detail.title}</h2>
      <p className="meta">
        {detail.id} · requirements {detail.requirements} · coverage{" "}
        {detail.requirement_coverage.toFixed(3)} · mutation{" "}
        {detail.mutation_score.toFixed(3)}
      </p>
      {detail.findings.length === 0 ? (
        <p className="none">No findings.</p>
      ) : (
        <ul className="findings">
          {detail.findings.map((finding, index) => (
            <li key={`${finding.check}:${finding.location}:${index}`}>
              <p className="finding-check">
                {finding.check} · {finding.severity}
              </p>
              <p className="finding-location">{finding.location}</p>
              <p>{finding.explanation}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(`request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

function message(reason: unknown): string {
  if (reason instanceof Error) {
    return reason.message;
  }
  return "The task list could not be loaded.";
}
