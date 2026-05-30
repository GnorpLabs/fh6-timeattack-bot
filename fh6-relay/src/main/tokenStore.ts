import * as fs from 'fs';
import * as path from 'path';
import { Config } from '../shared/types';

const DEFAULTS: Config = {
  token: '',
  apiUrl: '',
  discordId: '',
  discordUsername: '',
  udpPort: 20440,
  retentionDays: 30,
};

export class TokenStore {
  constructor(private readonly configPath: string) {}

  load(): Config {
    try {
      const raw = fs.readFileSync(this.configPath, 'utf8');
      return { ...DEFAULTS, ...JSON.parse(raw) };
    } catch {
      return { ...DEFAULTS };
    }
  }

  save(config: Config): void {
    fs.mkdirSync(path.dirname(this.configPath), { recursive: true });
    fs.writeFileSync(this.configPath, JSON.stringify(config, null, 2));
  }
}
