# Rebuild Engine

**Rebuild Engine**은 AI를 활용한 **바이브 코딩(Vibe Coding)** 방식으로 개발 중인 개인 2D 게임 엔진 프로젝트입니다.

기존 게임 엔진을 단순히 사용하는 것이 아니라, **AI의 도움을 받아 엔진 자체를 직접 만들어보면서 게임 엔진의 구조와 원리를 이해하는 것**을 목표로 합니다.

> ⚠️ 현재 개발 중인 실험적인 프로젝트입니다.\
> 엔진 구조와 기능은 개발 과정에서 계속 변경될 수 있습니다.

---

## 🤖 AI + Vibe Coding

Rebuild Engine은 일반적인 엔진 개발 방식과 조금 다릅니다.

이 프로젝트에서는 **AI에게 코드를 생성·수정하도록 요청하고, 직접 실행하고 테스트하면서 엔진을 발전시키는 바이브 코딩 방식**을 적극적으로 사용합니다.

개발 과정은 대략 다음과 같습니다.

```text
아이디어
   ↓
AI에게 구현 요청
   ↓
AI가 코드 작성
   ↓
직접 실행
   ↓
오류 및 문제 발견
   ↓
AI와 함께 수정
   ↓
기능 완성
   ↓
다음 기능 개발
```

하지만 AI가 모든 것을 알아서 만드는 것을 목표로 하지는 않습니다.

**코드가 실제로 어떻게 동작하는지 이해하고, 필요한 부분은 직접 수정하며 엔진을 발전시키는 것**을 중요하게 생각합니다.

---

## 🎯 프로젝트 목표

Rebuild Engine의 가장 큰 목표는

> **"게임을 만들면서 동시에 게임 엔진을 직접 이해해보자."**

입니다.

처음부터 Unity나 Unreal Engine과 같은 거대한 엔진을 만드는 것이 목표가 아닙니다.

작은 기능부터 직접 구현하고 하나씩 확장합니다.

```text
Game Loop
    ↓
Rendering
    ↓
Object System
    ↓
Sprite System
    ↓
Scene System
    ↓
Collision
    ↓
Physics
    ↓
Animation
    ↓
Editor
    ↓
Game Creation
```

---

# 🎮 주요 기능

## 🧩 Object System

게임에 필요한 오브젝트를 생성하고 관리합니다.

```text
Player
Enemy
NPC
Platform
Camera
```

오브젝트를 에디터에서 생성하고 배치할 수 있는 구조를 목표로 합니다.

---

## 🖼️ Sprite & Animation

스프라이트와 애니메이션을 서로 분리된 기능으로 관리하기보다는 **하나의 Sprite 시스템 안에서 함께 관리하는 구조**를 지향합니다.

```text
Sprite
 ├─ Image
 ├─ Animation
 │   ├─ Idle
 │   ├─ Run
 │   └─ Jump
 └─ Collision
```

게임메이커와 비슷하게 게임 제작자가 스프라이트를 쉽게 다룰 수 있는 워크플로를 목표로 합니다.

---

## 🗺️ Scene System

게임의 공간을 Scene으로 구성합니다.

```text
Scene
 ├─ Player
 ├─ Enemy
 ├─ Platform
 └─ Background
```

에디터에서 배치한 오브젝트를 저장하고 게임 실행 시 불러오는 것을 목표로 합니다.

---

## 🔧 Inspector

선택한 오브젝트의 속성을 확인하고 수정할 수 있는 Inspector를 제공합니다.

```text
Player

Transform
 ├─ Position
 ├─ Rotation
 └─ Scale

Sprite
 ├─ Sprite
 └─ Animation

Physics
 ├─ Collision
 ├─ Gravity
 └─ Mass
```

---

# 🖥️ Editor

Rebuild Engine의 중요한 목표 중 하나는 **게임을 실행하는 Runtime뿐만 아니라 직접 만든 Editor를 구축하는 것**입니다.

게임 오브젝트를 만들고, 스프라이트를 설정하고, Scene을 구성하고, 게임을 실행하는 과정을 하나의 에디터에서 처리하는 것이 목표입니다.

---

# 🛠️ 개발 방식

Rebuild Engine은 **AI를 개발 도구로 적극적으로 활용합니다.**

AI에게 다음과 같은 작업을 요청할 수 있습니다.

- 엔진 시스템 구현
- 코드 작성
- 코드 수정
- 오류 분석
- 기능 추가
- 구조 개선
- 에디터 기능 구현

그리고 직접 테스트하면서 결과를 확인합니다.

```text
AI
 │
 ├── 코드 생성
 ├── 오류 수정
 └── 기능 구현
        │
        ▼
   Rebuild Engine
        │
        ▼
    직접 테스트
        │
        ▼
      피드백
        │
        └──────────→ AI
```

따라서 Rebuild Engine은 **AI와 사람이 함께 개발하는 실험적인 엔진 프로젝트**라고 할 수 있습니다.

---

# 🚧 개발 현황

현재 **개발 중(Work In Progress)** 입니다.

---

# 🎮 목표 장르

Rebuild Engine은 특히 다음과 같은 **2D 게임**을 제작할 수 있는 엔진을 목표로 합니다.

- 플랫폼 게임
- 액션 게임
- 스토리 게임
- RPG
- 퍼즐 게임
- 실험적인 2D 게임

특히 **2D 사이드뷰 게임 제작**을 주요 목표로 합니다.

---

# 📌 Project Status

**Development / Experimental**

아직 완성된 상용 게임 엔진이 아닙니다.

API, 에디터 UI, 프로젝트 구조, 파일 형식 및 엔진 시스템은 개발 과정에서 크게 변경될 수 있습니다.

---

# 👨‍💻 Development Philosophy

> **AI가 코드를 만들고, 사람이 이해하고, 함께 엔진을 만든다.**

Rebuild Engine은 완벽한 엔진을 처음부터 만드는 프로젝트가 아닙니다.

**하나씩 만들고, 부수고, 고치고, 다시 만드는 과정 자체가 이 프로젝트입니다.**

---

# Rebuild Engine

### AI-assisted. Human-driven. Built from scratch.

**게임을 만드는 것에서 끝나지 않고,**\
**게임 엔진 자체를 다시 만들어본다.**
