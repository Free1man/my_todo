using Godot;
using System;
using System.Text;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;

public partial class MinimalTbsViewer : Node2D
{
    private HttpRequest _http = default!;
    private Queue<string> _candidates = new();
    private const string SessionsPath = "/sessions";
    private int _attempt = 0;

    public override void _Ready()
    {
        GD.Print("MinimalTbsViewer ready. Resolving API base...");
        _http = new HttpRequest();
        AddChild(_http);
        _http.RequestCompleted += OnCompleted;

        // 1) Env-var override
    var envBase = System.Environment.GetEnvironmentVariable("TBS_API_BASE");
        if (!string.IsNullOrWhiteSpace(envBase))
            _candidates.Enqueue(envBase.TrimEnd('/'));

        // 2) Sidecar next to the executable (written at export time)
        try
        {
            var exeDir = Path.GetDirectoryName(OS.GetExecutablePath()) ?? "";
            var sidecar = Path.Combine(exeDir, "tbs_config.json");
            if (File.Exists(sidecar))
            {
                var json = File.ReadAllText(sidecar);
                using var doc = JsonDocument.Parse(json);
                var root = doc.RootElement;
                if (root.TryGetProperty("base_url", out var baseProp) && baseProp.ValueKind == JsonValueKind.String)
                {
                    var baseUrl = baseProp.GetString();
                    if (!string.IsNullOrWhiteSpace(baseUrl)) _candidates.Enqueue(baseUrl!.TrimEnd('/'));
                }
            }
        }
        catch (Exception e)
        {
            GD.PushWarning($"Sidecar read failed: {e.Message}");
        }

    // 3) Host default (most common when running on desktop)
    _candidates.Enqueue("http://localhost:8000");

    // 4) Compose-internal DNS (only if the game runs in a container)
    _candidates.Enqueue("http://api:8000");

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
    var url = baseUrl + SessionsPath;
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
