# GUI and AI interface result

Current product name: **Atom Code Bug Finder Harness**, by Lucerna Labs, a division of Lucerna Media. The project folder and source paths in this historical report retain their original internal names.

The standalone project has a browser GUI, an installed desktop application menu entry, a local JSON API, and a stdio MCP server for AI agents. They use the same saved configuration catalog and run receipts. The runner continues to execute the chosen target and checker through the existing JSON-line process contract.

Open **Atom Code Bug Finder Harness** from the desktop application menu, or run `python3 launch_gui.py`. The launcher starts the server on `127.0.0.1:8765` and opens the browser. The page can copy the example into its config editor, save a new validated config, run it, stop it, and inspect status, scores, gates and witness inputs. The installed desktop entry and icon are in `packaging/` and `web/icon.svg`; the installed entry passed `desktop-file-validate` and launched through `gtk-launch`.

The AI interface is `mcp_server.py`. It exposes seven MCP tools: `list_configs`, `get_config`, `start_run`, `get_run`, `list_runs`, `read_receipt`, and `cancel_run`. It serves the current `2026-07-28` lifecycle and legacy `2025-11-25` initialization. The official MCP Python client 2.3.0 connected in both modes, listed all seven tools, and in modern mode started the example, polled it to success, and read 10 saved witness replays. The production server itself uses only Python standard-library modules.

Verification at the actual boundaries:

- The live browser showed a completed example run with first-hit scores 11 and 7, eight measured gates and ten saved witnesses. Starting a new run from the GUI changed its state from running to succeeded and displayed its receipt. Copying the example populated a valid config with absolute paths; saving it through the GUI succeeded. The test config was removed afterward. Browser console errors: zero.
- The HTTP integration exercised config creation, run start/poll/receipt and rejected a POST without the local request header. The server binds to loopback and checks Host and Origin. The `tests/ui_mcp_boundaries.py` script also exercised modern and legacy MCP framing.
- The cross-process run lock refused an overlapping start. `tests/cancel_run.py` cancelled a stalled run, observed the target child exit, retained cancelled status, and verified the lock was released. Source files remained unchanged.
- Python compilation passed for the new modules. The local launcher health endpoint returned `ready` after a cold start and after the installed app-menu launcher reused the running server.

The GUI serves locally and uses a saved configuration to determine what code can run. The MCP tools can run only named saved configurations; an AI cannot submit an arbitrary command to the MCP server. Neither interface generates a target wrapper or a trustworthy checker for an unknown repository. A selected project needs those two small pieces as described in `EXTERNAL-CODE.md`. Configured target and checker processes execute with the user's local permissions, so test project code in an appropriate checkout. Logs and receipts stay in the ignored `runs/` directory.

Setup and tool usage: [GUI-AND-AI.md](GUI-AND-AI.md). The [MCP tools specification](https://modelcontextprotocol.io/specification/2026-07-28/server/tools) and [stdio transport specification](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio) describe the protocol boundaries used by `mcp_server.py`.
