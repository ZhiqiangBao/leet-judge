from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("LOCAL_LEET_ROOT", str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from app.judge.engine import judge_source  # noqa: E402
from app.judge.languages import language_status  # noqa: E402
from app.services.problems import bank  # noqa: E402

AC_TWO_SUM = '''
class Solution:
    def twoSum(self, nums: list[int], target: int) -> list[int]:
        seen = {}
        for i, n in enumerate(nums):
            need = target - n
            if need in seen:
                return [seen[need], i]
            seen[n] = i
        return []
'''

WA_TWO_SUM = '''
class Solution:
    def twoSum(self, nums: list[int], target: int) -> list[int]:
        return [0, 0]
'''

CE_TWO_SUM = "class Solution:\n    def twoSum(self\n"

AC_CPP = r'''
class Solution {
public:
    vector<int> twoSum(vector<int>& nums, int target) {
        unordered_map<int,int> seen;
        for (int i = 0; i < (int)nums.size(); ++i) {
            int need = target - nums[i];
            if (seen.count(need)) return {seen[need], i};
            seen[nums[i]] = i;
        }
        return {};
    }
};
'''

AC_C = r'''
int* twoSum(int* nums, int numsSize, int target, int* returnSize) {
    for (int i = 0; i < numsSize; i++) {
        for (int j = i + 1; j < numsSize; j++) {
            if (nums[i] + nums[j] == target) {
                int* out = (int*)malloc(sizeof(int) * 2);
                out[0] = i;
                out[1] = j;
                *returnSize = 2;
                return out;
            }
        }
    }
    *returnSize = 0;
    return NULL;
}
'''

WA_C = r'''
int* twoSum(int* nums, int numsSize, int target, int* returnSize) {
    int* out = (int*)malloc(sizeof(int) * 2);
    out[0] = 0;
    out[1] = 0;
    *returnSize = 2;
    return out;
}
'''


def expect(name: str, result: dict, verdict: str) -> None:
    got = result.get("verdict")
    if got != verdict:
        raise SystemExit(f"[FAIL] {name}: expected {verdict}, got {got} details={result}")
    print(f"[OK] {name}: {verdict}")


def main() -> None:
    print("problems:", [p.slug for p in bank.list()])
    print("languages:", language_status())
    if not bank.list():
        raise SystemExit("no problems loaded")

    py_ok = any(x["id"] == "python3" and x["available"] for x in language_status())
    if not py_ok:
        raise SystemExit("python3 adapter not available on this machine (needed for selftest)")

    expect("python AC", judge_source("two-sum", "python3", AC_TWO_SUM), "AC")
    expect("python WA", judge_source("two-sum", "python3", WA_TWO_SUM), "WA")
    expect("python CE", judge_source("two-sum", "python3", CE_TWO_SUM), "CE")
    public_ac = judge_source("two-sum", "python3", AC_TWO_SUM, True)
    expect("python public-only AC", public_ac, "AC")
    if (public_ac.get("details") or {}).get("total") != 3:
        raise SystemExit(f"[FAIL] public-only should run 3 examples, got {public_ac}")
    AC_JS = """
class Solution {
    twoSum(nums, target) {
        const seen = new Map();
        for (let i = 0; i < nums.length; i++) {
            const need = target - nums[i];
            if (seen.has(need)) return [seen.get(need), i];
            seen.set(nums[i], i);
        }
        return [];
    }
}
"""
    WA_JS = """
class Solution {
    twoSum(nums, target) {
        return [0, 0];
    }
}
"""
    AC_TS = """
class Solution {
    twoSum(nums: number[], target: number): number[] {
        const seen = new Map<number, number>();
        for (let i = 0; i < nums.length; i++) {
            const need = target - nums[i];
            const j = seen.get(need);
            if (j !== undefined) return [j, i];
            seen.set(nums[i], i);
        }
        return [];
    }
}
"""
    js = next(x for x in language_status() if x["id"] == "javascript")
    if js["available"]:
        expect("javascript AC", judge_source("two-sum", "javascript", AC_JS), "AC")
        expect("javascript WA", judge_source("two-sum", "javascript", WA_JS), "WA")
        expect("javascript CE", judge_source("two-sum", "javascript", "class Solution { twoSum("), "CE")
    else:
        print("[SKIP] javascript not available here; Ubuntu host with node will run JS judging")

    ts = next(x for x in language_status() if x["id"] == "typescript")
    if ts["available"]:
        expect("typescript AC", judge_source("two-sum", "typescript", AC_TS), "AC")
        expect("typescript WA", judge_source("two-sum", "typescript", WA_JS), "WA")
        expect("typescript CE", judge_source("two-sum", "typescript", "class Solution { twoSum("), "CE")
    else:
        print("[SKIP] typescript not available here; Ubuntu host with node + tsc will run TS judging")

    cpp = next(x for x in language_status() if x["id"] == "cpp17")
    if cpp["available"]:
        expect("cpp AC", judge_source("two-sum", "cpp17", AC_CPP), "AC")
    else:
        print("[SKIP] cpp17 not available here; Ubuntu host with g++ will run C++ judging")

    clang = next(x for x in language_status() if x["id"] == "c")
    if clang["available"]:
        expect("c AC", judge_source("two-sum", "c", AC_C), "AC")
        expect("c WA", judge_source("two-sum", "c", WA_C), "WA")
        expect("c CE", judge_source("two-sum", "c", "int* twoSum("), "CE")
    else:
        print("[SKIP] c not available here; Ubuntu host with gcc will run C judging")

    AC_GO = """
package main

type Solution struct{}

func (sol *Solution) TwoSum(nums []int, target int) []int {
    seen := map[int]int{}
    for i, n := range nums {
        if j, ok := seen[target-n]; ok {
            return []int{j, i}
        }
        seen[n] = i
    }
    return nil
}
"""
    WA_GO = """
package main

type Solution struct{}

func (sol *Solution) TwoSum(nums []int, target int) []int {
    return []int{0, 0}
}
"""
    AC_RS = """
use std::collections::HashMap;
pub struct Solution;
impl Solution {
    pub fn two_sum(nums: Vec<i32>, target: i32) -> Vec<i32> {
        let mut seen = HashMap::new();
        for (i, n) in nums.into_iter().enumerate() {
            if let Some(&j) = seen.get(&(target - n)) {
                return vec![j, i as i32];
            }
            seen.insert(n, i as i32);
        }
        vec![]
    }
}
"""
    WA_RS = """
pub struct Solution;
impl Solution {
    pub fn two_sum(nums: Vec<i32>, target: i32) -> Vec<i32> {
        let _ = (nums, target);
        vec![0, 0]
    }
}
"""
    AC_ZIG = """
const Solution = struct {
    pub fn twoSum(self: @This(), nums: []const i32, target: i32) []i32 {
        _ = self;
        var i: usize = 0;
        while (i < nums.len) : (i += 1) {
            var j: usize = i + 1;
            while (j < nums.len) : (j += 1) {
                if (nums[i] + nums[j] == target) {
                    var out = std.heap.page_allocator.alloc(i32, 2) catch unreachable;
                    out[0] = @intCast(i);
                    out[1] = @intCast(j);
                    return out;
                }
            }
        }
        return &.{};
    }
};
"""
    WA_ZIG = """
const Solution = struct {
    pub fn twoSum(self: @This(), nums: []const i32, target: i32) []i32 {
        _ = self;
        _ = nums;
        _ = target;
        var out = std.heap.page_allocator.alloc(i32, 2) catch unreachable;
        out[0] = 0;
        out[1] = 0;
        return out;
    }
};
"""
    go = next(x for x in language_status() if x["id"] == "go")
    if go["available"]:
        expect("go AC", judge_source("two-sum", "go", AC_GO), "AC")
        expect("go WA", judge_source("two-sum", "go", WA_GO), "WA")
        expect("go CE", judge_source("two-sum", "go", "package main\nfunc ("), "CE")
    else:
        print("[SKIP] go not available here; Ubuntu host with golang-go will run Go judging")

    rs = next(x for x in language_status() if x["id"] == "rust")
    if rs["available"]:
        expect("rust AC", judge_source("two-sum", "rust", AC_RS), "AC")
        expect("rust WA", judge_source("two-sum", "rust", WA_RS), "WA")
        expect("rust CE", judge_source("two-sum", "rust", "pub struct Solution"), "CE")
    else:
        print("[SKIP] rust not available here; Ubuntu host with rustc will run Rust judging")

    zg = next(x for x in language_status() if x["id"] == "zig")
    if zg["available"]:
        expect("zig AC", judge_source("two-sum", "zig", AC_ZIG), "AC")
        expect("zig WA", judge_source("two-sum", "zig", WA_ZIG), "WA")
        expect("zig CE", judge_source("two-sum", "zig", "const Solution = struct {"), "CE")
    else:
        print("[SKIP] zig not available here; Ubuntu 26.04 host with zig 0.14 will run Zig judging")


    print("selftest passed")


if __name__ == "__main__":
    main()
