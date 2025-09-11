using Godot;
using System;
using System.Text;
using System.Text.Json;
using System.Collections.Generic;
using System.IO;
using SysEnv = System.Environment;

public partial class MinimalTbsViewer : Node2D
{
    // ---- HTTP / config ----
    private HttpRequest _http = default!;
    private readonly Queue<string> _candidates = new();
    private const string SessionsPath = "/sessions";
    private int _attempt = 0;

    // ---- Data ----
    private readonly List<SessionEntry> _entries = new();
    private int _selectedIndex = -1;
    private JsonElement? _currentMission = null; // when not null we render mission
    private JsonDocument? _openMissionDoc; // keep the active mission document alive

    private record SessionEntry(string Id, string Title, string MissionRaw);

    // ---- UI ----
    private CanvasLayer _ui = default!;
    private Control _overlay = default!;

    private PanelContainer _pickerPanel = default!;
    private ItemList _sessionList = default!;
    private Button _backBtn = default!;

    private PanelContainer _statusBar = default!;
    private Label _statusLabel = default!;

    // ---- Draw ----
    private float _tile = 48f;

    public override void _Ready()
    {
        GD.Print("MinimalTbsViewer ready. Resolving API base...");

        BuildUi();

        _http = new HttpRequest();
        AddChild(_http);
        _http.RequestCompleted += OnCompleted;

        var envBase = SysEnv.GetEnvironmentVariable("TBS_API_BASE");
        if (!string.IsNullOrWhiteSpace(envBase))
            _candidates.Enqueue(envBase!.TrimEnd('/'));

        TryReadSidecarBaseUrl();

        _candidates.Enqueue("http://localhost:8000");
        _candidates.Enqueue("http://api:8000");

        TryNext();
    }

    private void TryReadSidecarBaseUrl()
    {
        try
        {
            var exeDir = Path.GetDirectoryName(OS.GetExecutablePath()) ?? "";
            var sidecar = Path.Combine(exeDir, "tbs_config.json");
            if (File.Exists(sidecar))
            {
                var json = File.ReadAllText(sidecar);
                using var doc = JsonDocument.Parse(json);
                if (doc.RootElement.TryGetProperty("base_url", out var prop) &&
                    prop.ValueKind == JsonValueKind.String)
                {
                    var baseUrl = prop.GetString();
                    if (!string.IsNullOrWhiteSpace(baseUrl))
                        _candidates.Enqueue(baseUrl!.TrimEnd('/'));
                }
            }
        }
        catch (Exception e)
        {
            GD.PushWarning($"Sidecar read failed: {e.Message}");
        }
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

        if (code != 200)
        {
            GD.PushWarning("Non-200, trying next base...");
            TryNext();
            return;
        }

        try
        {
            using var doc = JsonDocument.Parse(text);
            _entries.Clear();

            foreach (var el in doc.RootElement.EnumerateArray())
            {
                var id = el.GetProperty("id").GetString() ?? "<missing>";
                var mission = el.GetProperty("mission");
                var missionRaw = mission.GetRawText(); // keep a safe copy
                var name = mission.TryGetProperty("name", out var nm) ? nm.GetString() ?? "Mission" : "Mission";

                int unitsCount = 0;
                if (mission.TryGetProperty("units", out var units))
                {
                    if (units.ValueKind == JsonValueKind.Object)
                        unitsCount = CountObjectProps(units);
                    else if (units.ValueKind == JsonValueKind.Array)
                        unitsCount = units.GetArrayLength();
                }

                var status = mission.TryGetProperty("status", out var st) ? st.GetString() ?? "" : "";
                var title = $"{name}  —  id={Truncate(id, 8)}  • units={unitsCount}  • status={status}";
                _entries.Add(new SessionEntry(id, title, missionRaw));
            }

            PopulatePicker();
            ShowPicker();
        }
        catch (Exception e)
        {
            GD.PushError($"Failed to parse /sessions: {e.Message}");
        }
    }

    private static int CountObjectProps(JsonElement obj)
    {
        int c = 0;
        foreach (var _ in obj.EnumerateObject()) c++;
        return c;
    }

    // ===================== UI BUILD =====================

    private void BuildUi()
    {
        _ui = new CanvasLayer { Name = "UI" };
        AddChild(_ui);

        _overlay = new Control { Name = "Overlay" };
        _overlay.SetAnchorsPreset(Control.LayoutPreset.FullRect);
        _overlay.MouseFilter = Control.MouseFilterEnum.Stop;
        _ui.AddChild(_overlay);

        // ---------- Session Picker (centered) ----------
        var center = new CenterContainer { Name = "Center" };
        center.SetAnchorsPreset(Control.LayoutPreset.FullRect);
        _overlay.AddChild(center);

        _pickerPanel = new PanelContainer { Name = "PickerPanel" };
        _pickerPanel.CustomMinimumSize = new Vector2(720, 420);
        center.AddChild(_pickerPanel);

        var pickerMargin = new MarginContainer();
        pickerMargin.AddThemeConstantOverride("margin_left", 24);
        pickerMargin.AddThemeConstantOverride("margin_top", 20);
        pickerMargin.AddThemeConstantOverride("margin_right", 24);
        pickerMargin.AddThemeConstantOverride("margin_bottom", 20);
        _pickerPanel.AddChild(pickerMargin);

        var v = new VBoxContainer();
        v.AddThemeConstantOverride("separation", 12); // Godot 4: theme constant, not a property
        pickerMargin.AddChild(v);

        var title = new Label { Text = "Select a Session" };
        title.AddThemeFontSizeOverride("font_size", 20);
        v.AddChild(title);

        _sessionList = new ItemList
        {
            SelectMode = ItemList.SelectModeEnum.Single,
            AutoHeight = false,
            CustomMinimumSize = new Vector2(660, 330)
        };
        v.AddChild(_sessionList);

        var buttons = new HBoxContainer { Alignment = BoxContainer.AlignmentMode.End };
        v.AddChild(buttons);

        _backBtn = new Button { Text = "Back", Disabled = true, TooltipText = "Close the game (no mission open)" };
        _backBtn.Pressed += () => GetTree().Quit(); // at picker: Back = exit
        buttons.AddChild(_backBtn);

        var openBtn = new Button { Text = "Open" };
        openBtn.Pressed += () => OpenSelected();
        buttons.AddChild(openBtn);

        _sessionList.ItemActivated += (index) => OpenByIndex((int)index);
        _sessionList.ItemSelected += (index) =>
        {
            _selectedIndex = (int)index;
            UpdateStatusForSelection();
        };

        // ---------- Bottom status bar ----------
        _statusBar = new PanelContainer { Name = "StatusBar", Visible = true };
        _statusBar.SetAnchorsPreset(Control.LayoutPreset.BottomWide);
        _statusBar.OffsetTop = -64;
        _statusBar.OffsetBottom = -16;
        _statusBar.OffsetLeft = 24;
        _statusBar.OffsetRight = -24;
        _overlay.AddChild(_statusBar);

        var sbMargin = new MarginContainer();
        sbMargin.AddThemeConstantOverride("margin_left", 12);
        sbMargin.AddThemeConstantOverride("margin_top", 8);
        sbMargin.AddThemeConstantOverride("margin_right", 12);
        sbMargin.AddThemeConstantOverride("margin_bottom", 8);
        _statusBar.AddChild(sbMargin);

        _statusLabel = new Label { Text = "Ready." };
        sbMargin.AddChild(_statusLabel);

        ShowPicker();
    }

    private void PopulatePicker()
    {
        _sessionList.Clear();
        for (int i = 0; i < _entries.Count; i++)
            _sessionList.AddItem($"{i + 1}. {_entries[i].Title}");

        _selectedIndex = _entries.Count > 0 ? 0 : -1;
        if (_selectedIndex >= 0) _sessionList.Select(_selectedIndex);
        UpdateStatusForSelection();
    }

    private void UpdateStatusForSelection()
    {
        if (_selectedIndex >= 0 && _selectedIndex < _entries.Count)
            _statusLabel.Text = _entries[_selectedIndex].Title;
        else
            _statusLabel.Text = "No session selected.";
    }

    private void ShowPicker()
    {
    _openMissionDoc?.Dispose();
    _openMissionDoc = null;
    _currentMission = null;
        _pickerPanel.Visible = true;
        _backBtn.Disabled = false;
        _statusBar.Visible = true;
        QueueRedraw();
    }

    private void HidePickerForMission()
    {
        _pickerPanel.Visible = false;
        _backBtn.Disabled = false;
    }

    private void OpenSelected()
    {
        if (_selectedIndex >= 0)
            OpenByIndex(_selectedIndex);
    }

    private void OpenByIndex(int idx)
    {
        if (idx < 0 || idx >= _entries.Count) return;

        var chosen = _entries[idx];
    _openMissionDoc?.Dispose();
    _openMissionDoc = JsonDocument.Parse(chosen.MissionRaw);
    _currentMission = _openMissionDoc.RootElement;
    _statusLabel.Text = $"Viewing: {chosen.Title} — press Esc to return.";
        HidePickerForMission();
        QueueRedraw();
    }

    public override void _UnhandledInput(InputEvent e)
    {
        if (e is InputEventKey k && k.Pressed && !k.Echo)
        {
            if (k.Keycode == Key.Escape || k.Keycode == Key.Backspace)
            {
                if (_currentMission is not null)
                    ShowPicker();
                else
                    GetTree().Quit();
            }
        }
    }

    // ===================== RENDER =====================

    public override void _Draw()
    {
        if (_currentMission is null) return;

    var mission = _currentMission.Value;
    if (!mission.TryGetProperty("map", out var map)) return;

    int w = map.GetProperty("width").GetInt32();
    int h = map.GetProperty("height").GetInt32();

        var vp = GetViewportRect().Size;
        var boardSize = new Vector2(w * _tile, h * _tile);
        var origin = (vp - boardSize) / 2f;

    if (map.TryGetProperty("tiles", out var tiles) && tiles.ValueKind == JsonValueKind.Array)
        {
            for (int y = 0; y < h; y++)
            {
                var row = tiles[y];
                for (int x = 0; x < w; x++)
                {
                    var cell = row[x];
                    var terrain = cell.GetProperty("terrain").GetString() ?? "plain";
            DrawRect(new Rect2(origin + new Vector2(x * _tile, y * _tile),
                       new Vector2(_tile - 1f, _tile - 1f)),
                 TerrainColor(terrain), true);
                }
            }
        }

        var gridCol = new Color(1f, 1f, 1f, 0.08f);
        for (int gx = 0; gx <= w; gx++)
            DrawLine(origin + new Vector2(gx * _tile, 0), origin + new Vector2(gx * _tile, h * _tile), gridCol, 1f);
        for (int gy = 0; gy <= h; gy++)
            DrawLine(origin + new Vector2(0, gy * _tile), origin + new Vector2(w * _tile, gy * _tile), gridCol, 1f);

        if (mission.TryGetProperty("units", out var unitsEl))
        {
            if (unitsEl.ValueKind == JsonValueKind.Object)
            {
                foreach (var u in unitsEl.EnumerateObject())
                    DrawUnit(origin, u.Value);
            }
            else if (unitsEl.ValueKind == JsonValueKind.Array)
            {
                foreach (var u in unitsEl.EnumerateArray())
                    DrawUnit(origin, u);
            }
        }
    }

    private void DrawUnit(Vector2 origin, JsonElement unit)
    {
        if (!unit.TryGetProperty("pos", out var posArr) || posArr.GetArrayLength() < 2) return;
        int ux = posArr[0].GetInt32();
        int uy = posArr[1].GetInt32();

        var side = unit.TryGetProperty("side", out var s) ? s.GetString() ?? "neutral" : "neutral";
        var alive = unit.TryGetProperty("alive", out var a) ? a.GetBoolean() : true;

        var center = origin + new Vector2(ux * _tile + _tile * 0.5f, uy * _tile + _tile * 0.5f);
        var r = _tile * 0.35f;

        var col = side switch
        {
            "player" => new Color(0.3f, 0.8f, 1f),
            "enemy"  => new Color(1f, 0.4f, 0.4f),
            _        => new Color(0.8f, 0.8f, 0.8f)
        };
        if (!alive) col = new Color(col, 0.35f);

        DrawCircle(center, r, col);
        DrawArc(center, r + 2f, 0f, Mathf.Tau, 24, new Color(0, 0, 0, 0.25f), 2f);
    }

    private static Color TerrainColor(string t) => t switch
    {
        "plain"  => new Color(0.12f, 0.12f, 0.12f),
        "forest" => new Color(0.10f, 0.16f, 0.10f),
        "hill"   => new Color(0.16f, 0.12f, 0.06f),
        "water"  => new Color(0.08f, 0.10f, 0.18f),
        "blocked"=> new Color(0.06f, 0.06f, 0.06f),
        _        => new Color(0.14f, 0.14f, 0.14f),
    };

    private static string Truncate(string s, int n) => s.Length <= n ? s : s.Substring(0, n);
}
