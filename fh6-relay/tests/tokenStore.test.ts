import * as os from 'os';
import * as path from 'path';
import * as fs from 'fs';
import { TokenStore } from '../src/main/tokenStore';

describe('TokenStore', () => {
  let tmpDir: string;
  let store: TokenStore;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'fh6relay-cfg-'));
    store = new TokenStore(path.join(tmpDir, 'config.json'));
  });

  afterEach(() => fs.rmSync(tmpDir, { recursive: true }));

  it('returns defaults when no config file exists', () => {
    const cfg = store.load();
    expect(cfg.udpPort).toBe(20440);
    expect(cfg.retentionDays).toBe(30);
    expect(cfg.token).toBe('');
  });

  it('saves and reloads config', () => {
    const cfg = store.load();
    cfg.token = 'abc123';
    cfg.apiUrl = 'https://example.com';
    store.save(cfg);

    const store2 = new TokenStore(path.join(tmpDir, 'config.json'));
    const reloaded = store2.load();
    expect(reloaded.token).toBe('abc123');
    expect(reloaded.apiUrl).toBe('https://example.com');
  });
});
