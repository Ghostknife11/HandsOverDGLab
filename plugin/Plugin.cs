// SPDX-License-Identifier: MIT
using System.Collections.Concurrent;
using System.Diagnostics;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using BepInEx;
using BepInEx.Unity.IL2CPP;
using HarmonyLib;
using Jaws.Gameplay.Character;
using Jaws.Gameplay.General;
using Jaws.Gameplay.Jaws;
using Jaws.General.GameState;
using UnityEngine;

namespace HandsOverDGLab;

[BepInPlugin("local.handsover.dglab", "Hands Over DG-LAB", "0.1.3")]
public sealed class Plugin : BasePlugin
{
    internal static Plugin Instance = null!;
    internal static CharacterManager? Local;
    internal static JawsGameCoordinator? Coordinator;
    internal static volatile bool Gameplay, Paused;
    internal static EventBridge Bridge = null!;
    private static string? lastAction;
    internal static void Guard(Action action)
    {
        try { action(); } catch (Exception e) { Instance.Log.LogWarning($"Event skipped: {e.Message}"); }
    }

    public override void Load()
    {
        Instance = this;
        int port = Config.Bind("Bridge", "Port", 17896, "Local desktop GUI TCP port").Value;
        if (port is < 1024 or > 65535) throw new ArgumentOutOfRangeException(nameof(port));
        Bridge = new EventBridge(port, Log);
        try
        {
            new Harmony("local.handsover.dglab").PatchAll(typeof(Plugin).Assembly);
            AddComponent<Monitor>();
            Bridge.Hooks = true;
            Log.LogInfo("READY: ClientPressButtonReaction and lifecycle hooks installed; desktop applies APP limit percentages.");
            File.AppendAllText(Path.Combine(Paths.BepInExRootPath, "HandsOverDGLab.events.jsonl"),
                JsonSerializer.Serialize(new { kind = "ready", time = DateTimeOffset.UtcNow, version = "0.1.3" }) + "\n");
        }
        catch (Exception e)
        {
            new Harmony("local.handsover.dglab").UnpatchSelf();
            Bridge.Hooks = false;
            Log.LogError($"Hooks unavailable; no game events will be emitted: {e}");
        }
        Bridge.Start();
    }

    internal static bool IsLocal(CharacterManager c) => c != null && c.IsSpawned && c.IsOwner
        && c.NetworkManager != null && c.OwnerClientId == c.NetworkManager.LocalClientId;

    internal static void Reaction(CharacterManager c, JawsPressButtonResult result)
    {
        if (!Bridge.Hooks || !IsLocal(c) || Paused || Coordinator == null) return;
        string? outcome = result switch {
            JawsPressButtonResult.UsualButtonPressed or JawsPressButtonResult.SaveEffectTriggered => "fake",
            JawsPressButtonResult.TrappedButtonPressed or JawsPressButtonResult.TrapEffectTriggered => "real",
            _ => null
        };
        if (outcome == null) return;
        Local = c;
        string key = $"{Coordinator.Pointer}:{Coordinator.RoundNumber}:{Coordinator.TotalTurnsNumber}:{c.NetworkObjectId}";
        if (key == lastAction) return;
        lastAction = key;
        Bridge.Active = true;
        var evt = Bridge.Send("result", outcome, c.OwnerClientId, key);
        Instance.Log.LogInfo($"Local result: {result} => {outcome}; round={Coordinator.RoundNumber}, turn={Coordinator.TotalTurnsNumber}");
        File.AppendAllText(Path.Combine(Paths.BepInExRootPath, "HandsOverDGLab.events.jsonl"), evt + "\n");
    }

    internal static void Stop(string reason)
    {
        Bridge.Active = false;
        Bridge.Send("stop", reason);
    }

    [HarmonyPatch(typeof(CharacterManager), nameof(CharacterManager.ClientPressButtonReaction))]
    private static class ResultHook {
        static void Postfix(CharacterManager __instance, JawsPressButtonResult pressButtonResult)
            => Guard(() => Reaction(__instance, pressButtonResult));
    }
    [HarmonyPatch(typeof(CharacterManager), nameof(CharacterManager.OnNetworkSpawn))]
    private static class SpawnHook {
        static void Postfix(CharacterManager __instance) => Guard(() => { if (IsLocal(__instance)) Local = __instance; });
    }
    [HarmonyPatch(typeof(CharacterManager), nameof(CharacterManager.OnNetworkDespawn))]
    private static class DespawnHook {
        static void Prefix(CharacterManager __instance) => Guard(() => {
            if (Local != null && Local.Pointer == __instance.Pointer) { Stop("despawn"); Local = null; }
        });
    }
    [HarmonyPatch(typeof(JawsGameCoordinator), nameof(JawsGameCoordinator.OnNetworkSpawn))]
    private static class CoordinatorHook {
        static void Postfix(JawsGameCoordinator __instance) => Guard(() => { Coordinator = __instance; lastAction = null; });
    }
    [HarmonyPatch(typeof(JawsGameCoordinator), nameof(JawsGameCoordinator.ClientHandleShutdown))]
    private static class ShutdownHook { static void Prefix() => Guard(() => { Stop("shutdown"); Local = null; Coordinator = null; }); }
    [HarmonyPatch(typeof(GameStateService), nameof(GameStateService.SetGameState))]
    private static class SceneHook {
        static void Postfix(GameStateType gameState) => Guard(() => {
            Gameplay = gameState == GameStateType.Gameplay;
            if (!Gameplay) { Stop("scene"); Local = null; Coordinator = null; Paused = false; }
        });
    }
    [HarmonyPatch(typeof(PauseController), nameof(PauseController.SetPauseState))]
    private static class PauseHook {
        static void Postfix(bool state) => Guard(() => { Paused = state; if (state) Stop("pause"); });
    }

    public sealed class Monitor : MonoBehaviour
    {
        public Monitor(IntPtr pointer) : base(pointer) { }
        private float next;
        public void Update()
        {
            if (Time.unscaledTime < next) return;
            next = Time.unscaledTime + .1f;
            Guard(() => {
                if (Local == null && Coordinator != null && Coordinator.MyCharacter != null && IsLocal(Coordinator.MyCharacter))
                    Local = Coordinator.MyCharacter;
                bool active = Gameplay && !Paused && Local != null && IsLocal(Local)
                    && Local.NetworkManager.IsListening;
                if (Bridge.Active && !active) Stop("inactive");
                Bridge.Active = active;
            });
        }
        public void OnApplicationQuit() { Guard(() => Stop("quit")); Bridge?.Dispose(); }
    }
}

internal sealed class EventBridge : IDisposable
{
    private readonly int port;
    private readonly BepInEx.Logging.ManualLogSource log;
    private readonly CancellationTokenSource cancellation = new();
    private readonly ConcurrentQueue<(string Line, long At)> queue = new();
    private readonly SemaphoreSlim wake = new(0, 1);
    private readonly string session = Guid.NewGuid().ToString("N");
    private long sequence;
    public volatile bool Active, Hooks;
    private Task? worker;
    public EventBridge(int port, BepInEx.Logging.ManualLogSource log) { this.port = port; this.log = log; }
    public void Start() => worker = Task.Run(Run);
    private string Frame(string kind, string? result = null, ulong? owner = null, string? action = null) =>
        JsonSerializer.Serialize(new { v = 1, kind, session, seq = Interlocked.Increment(ref sequence),
            timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(), active = Active, hooks = Hooks,
            paused = Plugin.Paused, gameplay = Plugin.Gameplay, result, owner, action });
    public string Send(string kind, string? result = null, ulong? owner = null, string? action = null)
    {
        string line = Frame(kind, result, owner, action);
        if (queue.Count < 32) queue.Enqueue((line, Environment.TickCount64));
        try { wake.Release(); } catch (SemaphoreFullException) { }
        return line;
    }
    private async Task Run()
    {
        var token = cancellation.Token;
        while (!token.IsCancellationRequested)
        {
            try
            {
                using var client = new TcpClient { NoDelay = true };
                await client.ConnectAsync("127.0.0.1", port, token);
                while (queue.TryDequeue(out _)) { } // Never replay disconnected events.
                using var writer = new StreamWriter(client.GetStream(), new UTF8Encoding(false)) { AutoFlush = true };
                await writer.WriteLineAsync(Frame("hello"));
                long heartbeat = Environment.TickCount64;
                while (!token.IsCancellationRequested)
                {
                    while (queue.TryDequeue(out var item))
                        if (Environment.TickCount64 - item.At < 1000) await writer.WriteLineAsync(item.Line);
                    if (Environment.TickCount64 - heartbeat >= 500)
                    {
                        await writer.WriteLineAsync(Frame("heartbeat"));
                        heartbeat = Environment.TickCount64;
                    }
                    await wake.WaitAsync(100, token);
                }
            }
            catch (OperationCanceledException) { break; }
            catch (Exception) { while (queue.TryDequeue(out _)) { } }
            try { await Task.Delay(500, token); } catch (OperationCanceledException) { break; }
        }
    }
    public void Dispose()
    {
        Active = false;
        Send("stop", "quit");
        try { worker?.Wait(120); } catch { }
        cancellation.Cancel();
    }
}
