using System.Collections.Concurrent;
using System.Diagnostics;
using System.Text.Json;
using Microsoft.AspNetCore.Http.Features;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.UseUrls("http://127.0.0.1:5278");
builder.Services.Configure<FormOptions>(o => o.MultipartBodyLengthLimit = 1_000_000_000);
builder.WebHost.ConfigureKestrel(o => o.Limits.MaxRequestBodySize = 1_000_000_000);
var app = builder.Build();
var data = Environment.GetEnvironmentVariable("PHRASE_DATA") ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "PhraseStudio");
Directory.CreateDirectory(data);
var engine = Path.Combine(app.Environment.ContentRootPath, "engine", "studio.py");
var packagedEngine = Path.Combine(app.Environment.ContentRootPath, "engine", "phrase-engine.exe");
var python = Environment.GetEnvironmentVariable("PHRASE_PYTHON") ?? (OperatingSystem.IsWindows() ? "python" : "python3");
var jobs = new ConcurrentDictionary<string, RenderJob>();
var running = new ConcurrentDictionary<string, Process>();
var cancelled = new ConcurrentDictionary<string, bool>();
var gate = new SemaphoreSlim(1, 1);
var jsonOptions = new JsonSerializerOptions(JsonSerializerDefaults.Web);

bool ValidId(string value) => Guid.TryParseExact(value, "N", out _);
string ProjectPath(string id) => Path.Combine(data, id);
void SaveJob(RenderJob job)
{
    jobs[job.Id] = job;
    var path = Path.Combine(ProjectPath(job.ProjectId), "job.json");
    File.WriteAllText(path + ".tmp", JsonSerializer.Serialize(job, jsonOptions));
    File.Move(path + ".tmp", path, true);
}

async Task RunEngine(string[] arguments, Action<JsonElement>? progress = null, string? jobId = null)
{
    var info = new ProcessStartInfo(File.Exists(packagedEngine) ? packagedEngine : python) { RedirectStandardOutput = true, RedirectStandardError = true, UseShellExecute = false, CreateNoWindow = true };
    if (!File.Exists(packagedEngine)) info.ArgumentList.Add(engine);
    foreach (var argument in arguments) info.ArgumentList.Add(argument);
    if (jobId != null && cancelled.ContainsKey(jobId)) throw new InvalidOperationException("Rendering cancelled");
    using var process = Process.Start(info) ?? throw new InvalidOperationException("Could not start Python");
    if (jobId != null)
    {
        running[jobId] = process;
        if (cancelled.ContainsKey(jobId)) process.Kill(entireProcessTree: true);
    }
    var errors = process.StandardError.ReadToEndAsync();
    var message = "Media engine failed";
    try
    {
        while (await process.StandardOutput.ReadLineAsync() is { } line)
        {
            try
            {
                using var parsed = JsonDocument.Parse(line);
                if (parsed.RootElement.TryGetProperty("error", out var e)) message = e.GetString() ?? message;
                progress?.Invoke(parsed.RootElement);
            }
            catch (JsonException) { /* Ignore non-JSON dependency diagnostics. */ }
        }
        await process.WaitForExitAsync();
        var stderr = await errors;
        if (process.ExitCode != 0) throw new InvalidOperationException(message == "Media engine failed" && stderr.Length > 0 ? stderr[..Math.Min(stderr.Length, 2000)] : message);
    }
    finally { if (jobId != null) running.TryRemove(jobId, out _); }
}

// Only this local UI may mutate state. Do not permit an arbitrary website to invoke local rendering.
app.Use(async (context, next) =>
{
    if (context.Request.Host.Host != "127.0.0.1") { context.Response.StatusCode = 403; return; }
    if (context.Request.Method != "GET" && context.Request.Method != "HEAD")
    {
        var origin = context.Request.Headers.Origin.ToString();
        if (context.Request.Headers["X-Phrase-Studio"] != "local" || (origin.Length > 0 && origin != "http://127.0.0.1:5278"))
        { context.Response.StatusCode = 403; return; }
    }
    context.Response.Headers["X-Content-Type-Options"] = "nosniff";
    context.Response.Headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self'; script-src 'self'; media-src 'self'; img-src 'self'; frame-ancestors 'none'";
    try { await next(context); }
    catch (Exception ex) when (!context.Response.HasStarted)
    {
        context.Response.StatusCode = 400;
        await context.Response.WriteAsJsonAsync(new { error = ex.Message });
    }
});
app.UseDefaultFiles();
app.UseStaticFiles();

app.MapGet("/api/health", async () =>
{
    try { await RunEngine(["health"]); return Results.Ok(new { ready = true, message = "Ready to render. Your recordings stay on this computer." }); }
    catch (Exception e) { return Results.Ok(new { ready = false, message = "Setup needed: " + e.Message }); }
});

app.MapGet("/api/projects", () =>
{
    var list = new List<object>();
    foreach (var folder in Directory.EnumerateDirectories(data).Where(p => ValidId(Path.GetFileName(p))))
    {
        var file = Path.Combine(folder, "project.json");
        if (!File.Exists(file)) continue;
        using var doc = JsonDocument.Parse(File.ReadAllText(file));
        list.Add(new { id = Path.GetFileName(folder), title = doc.RootElement.GetProperty("title").GetString(), importedAt = File.GetCreationTimeUtc(file) });
    }
    return Results.Ok(list);
});

app.MapPost("/api/projects", async (HttpRequest request) =>
{
    var form = await request.ReadFormAsync();
    var file = form.Files.GetFile("package");
    if (file == null || file.Length == 0 || file.Length > 1_000_000_000) return Results.BadRequest(new { error = "Choose a completed Phase 2 ZIP under 1 GB." });
    var id = Guid.NewGuid().ToString("N");
    var temporary = Path.Combine(data, id + ".upload");
    try
    {
        await using (var stream = File.Create(temporary)) await file.CopyToAsync(stream);
        await RunEngine(["import", "--input", temporary, "--project", ProjectPath(id)]);
        return Results.Ok(new { id });
    }
    finally { if (File.Exists(temporary)) File.Delete(temporary); }
});

app.MapGet("/api/projects/{id}", (string id) => ValidId(id) && File.Exists(Path.Combine(ProjectPath(id), "project.json"))
    ? Results.File(Path.Combine(ProjectPath(id), "project.json"), "application/json") : Results.NotFound());

app.MapGet("/api/settings", () =>
{
    var file = Path.Combine(data, "settings.json");
    return File.Exists(file) ? Results.File(file, "application/json") : Results.Ok(new { preset = "master" });
});
app.MapPost("/api/settings", (Settings settings) =>
{
    if (settings.Preset is not ("master" or "preview")) return Results.BadRequest();
    File.WriteAllText(Path.Combine(data, "settings.json"), JsonSerializer.Serialize(settings, jsonOptions));
    return Results.Ok(settings);
});

app.MapPost("/api/projects/{id}/render", async (string id, Settings settings) =>
{
    if (!ValidId(id) || !File.Exists(Path.Combine(ProjectPath(id), "project.json"))) return Results.NotFound();
    if (settings.Preset is not ("master" or "preview")) return Results.BadRequest(new { error = "Unknown preset" });
    if (!await gate.WaitAsync(0)) return Results.Conflict(new { error = "A video is rendering. Finish or cancel it first." });
    var job = new RenderJob(Guid.NewGuid().ToString("N"), id, "rendering", 0, "Preparing your video", null);
    SaveJob(job);
    _ = Task.Run(async () =>
    {
        try
        {
            var output = Path.Combine(ProjectPath(id), job.Id + ".mp4");
            await RunEngine(["render", "--project", ProjectPath(id), "--output", output, "--preset", settings.Preset], result =>
            {
                if (result.TryGetProperty("progress", out var p))
                {
                    job = job with { Progress = p.GetInt32(), Message = result.GetProperty("message").GetString() ?? "Rendering" };
                    SaveJob(job);
                }
            }, job.Id);
            job = job with { Status = "completed", Progress = 100, Message = "Your video is ready", Download = $"/api/projects/{id}/video/{job.Id}" };
        }
        catch (Exception e) { job = job with { Status = cancelled.ContainsKey(job.Id) ? "cancelled" : "failed", Message = cancelled.ContainsKey(job.Id) ? "Rendering cancelled. Your recordings are safe." : e.Message }; }
        finally { SaveJob(job); gate.Release(); }
    });
    return Results.Ok(job);
});

app.MapGet("/api/projects/{id}/job", (string id) =>
{
    if (!ValidId(id)) return Results.NotFound();
    var file = Path.Combine(ProjectPath(id), "job.json");
    if (!File.Exists(file)) return Results.NoContent();
    var job = JsonSerializer.Deserialize<RenderJob>(File.ReadAllText(file), jsonOptions)!;
    if (job.Status == "rendering" && !jobs.ContainsKey(job.Id)) job = job with { Status = "failed", Message = "The app closed during rendering. Generate again; your recordings are safe." };
    return Results.Ok(job);
});

app.MapPost("/api/jobs/{id}/cancel", (string id) =>
{
    if (!ValidId(id)) return Results.NotFound();
    if (jobs.TryGetValue(id, out var job) && job.Status == "rendering") cancelled[id] = true;
    if (running.TryGetValue(id, out var process)) { try { process.Kill(entireProcessTree: true); } catch (InvalidOperationException) { } }
    return Results.Ok();
});

app.MapGet("/api/projects/{id}/video/{jobId}", (string id, string jobId) =>
{
    if (!ValidId(id) || !ValidId(jobId)) return Results.NotFound();
    var path = Path.Combine(ProjectPath(id), jobId + ".mp4");
    return File.Exists(path) ? Results.File(path, "video/mp4", fileDownloadName: "phrase-studio.mp4", enableRangeProcessing: true) : Results.NotFound();
});
app.Lifetime.ApplicationStopping.Register(() =>
{
    foreach (var p in running.Values) { try { p.Kill(entireProcessTree: true); } catch (InvalidOperationException) { } }
});
if (Environment.GetEnvironmentVariable("PHRASE_OPEN_BROWSER") == "1")
    app.Lifetime.ApplicationStarted.Register(() => Process.Start(new ProcessStartInfo("http://127.0.0.1:5278") { UseShellExecute = true }));
app.Run();

record Settings(string Preset);
record RenderJob(string Id, string ProjectId, string Status, int Progress, string Message, string? Download);
