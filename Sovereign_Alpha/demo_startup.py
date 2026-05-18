#!/usr/bin/env python3
"""
🚀 ZAIR 完整服务栈启动演示
启动 Validator 和 Miner，展示端到端的工作流
"""

from eth_account.messages import encode_defunct
from eth_account import Account
import asyncio
import sys
import json
import os
import time
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent / "zair-validator" / "src"))
sys.path.insert(0, str(Path(__file__).parent / "zair-miner" / "src"))


print("=" * 80)
print("🎯 ZAIR Protocol - 完整服务栈演示")
print("=" * 80)

# ============================================================================
# 第一步：验证 Validator 导入
# ============================================================================
print("\n[第一步] 验证 Validator 导入...")
try:
    from validator import HiveMindValidator
    validator = HiveMindValidator()
    print("✅ Validator 导入成功！")
except Exception as e:
    print(f"❌ 错误: {e}")
    sys.exit(1)

# ============================================================================
# 第二步：显示网络状态
# ============================================================================
print("\n[第二步] 显示网络状态...")
try:
    status = validator.get_network_status()
    print("✅ 网络状态:")
    print(json.dumps(status, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# 第三步：生成测试账户
# ============================================================================
print("\n[第三步] 生成 Ethereum 账户...")
try:
    account = Account.create()
    print(f"✅ 账户已创建")
    print(f"   地址: {account.address}")
    print(f"   私钥: {account.key.hex()}")
except Exception as e:
    print(f"❌ 错误: {e}")
    sys.exit(1)

# ============================================================================
# 第四步：测试签名
# ============================================================================
print("\n[第四步] 测试 EIP-191 签名...")
try:
    test_data = json.dumps({
        "node_name": "TestNode",
        "asset_id": "RWA-001",
        "composite_risk_score": 42,
        "confidence_level": 85,
        "timestamp": "2026-05-18T12:00:00Z"
    }, sort_keys=True)

    message = encode_defunct(text=test_data)
    signed = account.sign_message(message)
    signature = signed.signature.hex()

    print("✅ 签名已生成")
    print(f"   消息: {test_data[:50]}...")
    print(f"   签名: {signature[:20]}...")

    # 验证签名
    recovered = Account.recover_message(message, signature=signature)
    print(f"   恢复地址: {recovered}")
    print(
        f"   签名验证: {'✅ 通过' if recovered.lower() == account.address.lower() else '❌ 失败'}")
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# 第五步：提交测试向量
# ============================================================================
print("\n[第五步] 提交测试 Risk Vector...")
try:
    test_vector = {
        "node_name": "TestNode",
        "timestamp": "2026-05-18T12:00:00Z",
        "asset_id": "RWA-001",
        "legal_risk": 35,
        "liquidity_risk": 42,
        "smart_contract_risk": 28,
        "counterparty_risk": 31,
        "yield_sustainability": 75,
        "composite_risk_score": 38.2,
        "confidence_level": 85,
        "regional_sentiment": "positive",
        "local_data_signals": {"region": "MEA", "bias_type": "positive"}
    }

    print("✅ 测试向量已创建")
    print(json.dumps({k: v for k, v in list(
        test_vector.items())[:5]}, indent=2))
    print("   ...")
except Exception as e:
    print(f"❌ 错误: {e}")

# ============================================================================
# 总结
# ============================================================================
print("\n" + "=" * 80)
print("✨ 演示完成！")
print("=" * 80)
print("""
接下来的步骤：

1️⃣  启动 Validator API（Terminal 1）:
   cd zair-validator
   python -m uvicorn src.api:app --reload --port 8001

2️⃣  启动 Miner（Terminal 2）:
   cd zair-miner
   python src/miner.py --node-name MyNode --region MEA

3️⃣  查看 OpenAPI 文档:
   http://localhost:8001/docs

4️⃣  查看 Leaderboard:
   curl http://localhost:8001/leaderboard

💡 更多信息: 查看 README.md
""")
