<p align="center">
  <img src="../res/logo-header.svg" alt="BlinkDesk - 局域网远程控制"><br>
  <a href="#功能特性">功能</a> •
  <a href="#使用方法">使用</a> •
  <a href="#路线图">路线图</a> •
  <a href="#从源码构建">编译</a> •
  <a href="#截图">截图</a><br>
  [<a href="../README.md">English</a>] | [<a href="README-ZH.md">中文</a>]
</p>

# BlinkDesk — 局域网远程控制

BlinkDesk 是基于 [RustDesk](https://github.com/rustdesk/rustdesk) 开发的、**面向局域网（LAN）**的远程控制工具。

它用于解决局域网内缺少专用远程控制工具的问题：无需公网、无需注册/中继服务器，只要在同一局域网内，即可通过以下信息直接连接目标主机：

- **IP 地址** —— 局域网 IP，例如 `192.168.1.100`
- **端口** —— 可配置，默认 `21118`
- **用户名**
- **密码**

全程在局域网内完成，数据不出内网。

> [!CAUTION]
> **免责声明：** 本软件开发者不纵容或支持任何不道德或非法的使用行为。未经授权的访问、控制或侵犯隐私等行为严格违反我们的准则。请仅在您拥有或获得授权的主机上使用。

## 功能特性

- **局域网直连** —— 通过 IP + 端口 + 用户名 + 密码直接连接。
- **低延迟** —— 局域网内远程桌面控制。
- **成熟底座** —— 基于 RustDesk 代码库：屏幕采集、输入控制、剪贴板、文件传输等能力。
- **无需服务器** —— 局域网内点对点直连，数据不出内网。

### 路线图

- [ ] 局域网直连（IP + 端口 + 用户名 + 密码）
- [ ] SSH 隧道支持
- [ ] SOCKS5 代理支持
- [ ] 连接历史与收藏
- [ ] 跨子网 / VLAN 穿透

## 从源码构建

前置条件：Rust 工具链、C++ 编译环境、[vcpkg](https://github.com/microsoft/vcpkg) 并设置 `VCPKG_ROOT` 环境变量。

> 本项目使用 vcpkg **manifest 模式**，请直接运行 `vcpkg install`，**不要**携带包名参数。

**Windows**

```sh
vcpkg install --triplet x64-windows-static
cargo run
```

**Linux / macOS**

```sh
vcpkg install
cargo run
```

## 截图

_敬请期待。_

## 许可证

GNU Affero General Public License v3.0 —— 详见 [LICENCE](../LICENCE)。
