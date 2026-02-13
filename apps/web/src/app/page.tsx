import { BookOpen, BarChart3, Users, FileText } from "lucide-react";
import Link from "next/link";

export default function Home() {
  return (
    <div className="max-w-3xl mx-auto py-12">
      <div className="text-center mb-16 animate-fade-in-up">
        <h1
          className="text-5xl font-light tracking-tight mb-4"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Biblical Evals
        </h1>
        <p className="text-lg text-muted-foreground leading-relaxed max-w-xl mx-auto">
          A framework for evaluating how large language models respond to
          questions about the Bible and Christianity.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-12">
        {[
          {
            icon: BookOpen,
            title: "Curated Questions",
            desc: "Theological, factual, and interpretive questions spanning key areas of biblical scholarship.",
            delay: "animate-delay-1",
          },
          {
            icon: BarChart3,
            title: "Multi-Model Comparison",
            desc: "Run evaluations across GPT-4o, Claude, Gemini, and more with side-by-side analysis.",
            delay: "animate-delay-1",
          },
          {
            icon: Users,
            title: "Blind Review",
            desc: "Human reviewers score responses without knowing which model generated them.",
            delay: "animate-delay-2",
          },
          {
            icon: FileText,
            title: "Academic Reports",
            desc: "Generate detailed reports with per-model breakdowns, bias detection, and statistical analysis.",
            delay: "animate-delay-2",
          },
        ].map(({ icon: Icon, title, desc, delay }) => (
          <div
            key={title}
            className={`animate-fade-in-up ${delay} p-6 rounded-lg border border-border/60 bg-card/50 hover:bg-card/80 transition-colors`}
          >
            <Icon className="h-5 w-5 text-primary mb-3" />
            <h3
              className="text-lg font-medium mb-1"
              style={{ fontFamily: "var(--font-display)" }}
            >
              {title}
            </h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {desc}
            </p>
          </div>
        ))}
      </div>

      <div className="text-center animate-fade-in-up animate-delay-3">
        <Link
          href="/evaluations"
          className="inline-flex items-center gap-2 px-6 py-2.5 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors"
        >
          View Evaluations
        </Link>
      </div>
    </div>
  );
}
