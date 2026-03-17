/**
 * Auto-register all command modules.
 * Import this once at startup to populate the command registry.
 */
import { registerNavigationCommands } from './navigation.js';
import { registerQueryCommands } from './query.js';

export function registerAllCommands(): void {
  registerNavigationCommands();
  registerQueryCommands();
}
