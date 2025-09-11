using Godot;
using System;
using System.Text;
using System.Collections.Generic;

public partial class MinimalTbsViewer : Node2D
{
    private HttpRequest _http = default!;
    private Queue<string> _candidates = new();
    private string _sessionsPath = System.Environment.GetEnvironmentVariable("TBS_SESSIONS_PATH") ?? "/sessions";
    private int _attempt = 0;

    public override void _Ready()
    {
        GD.Print("MinimalTbsViewer ready. Resolving API base...");
        _http = new HttpRequest();
        AddChild(_http);
        _http.RequestCompleted += OnCompleted;

    var envBase = System.Environment.GetEnvironmentVariable("TBS_API_BASE");
        if (!string.IsNullOrWhiteSpace(envBase)) _candidates.Enqueue(envBase.TrimEnd('/'));
        _candidates.Enqueue("http://api:8000");       // Compose internal DNS
        _candidates.Enqueue("http://localhost:8000"); // Host

        TryNext();
    }

    private void TryNext()
    {
        _attempt++;
        if (_candidates.Count == 0)
        {
            GD.PushError("No reachable API base URL.");
            GetTree().Quit(2);
            return;
        }
        var baseUrl = _candidates.Dequeue();
        var url = baseUrl + _sessionsPath;
        GD.Print($"Attempt #{_attempt}: GET {url}");
        var err = _http.Request(url);
        if (err != Error.Ok)
        {
            GD.PushWarning($"Failed to start HTTP request ({err}), trying next base...");
            CallDeferred(nameof(TryNext));
        }
    }

    private void OnCompleted(long result, long code, string[] headers, byte[] body)
    {
        if (result != (long)HttpRequest.Result.Success || code == 0)
        {
            GD.PushWarning($"HTTP transport failed (result={result}, code={code}). Trying next base...");
            TryNext();
            return;
        }

        var text = Encoding.UTF8.GetString(body ?? Array.Empty<byte>());
        GD.Print($"GET /sessions -> {code}");
        GD.Print(text);

        if (code == 200) GetTree().Quit(0);
        else { GD.PushWarning("Non-200, trying next base..."); TryNext(); }
    }
}
