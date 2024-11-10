

### Metasploitの設定

1. Metasploit RPC serverの起動:

``` bash
msfrpcd -P your_password -S -a 127.0.0.1
```

- -P: RPCサーバーのパスワード設定
- -S: SSL無効化（テスト環境のみ）
- -a: リッスンアドレス