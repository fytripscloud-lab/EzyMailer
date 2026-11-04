import { renderHook } from "@testing-library/react";
import { act } from "react";

import { usePolling } from "@/lib/usePolling";

describe("usePolling", () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("calls fn immediately and then on each interval while active", async () => {
    const fn = jest.fn().mockResolvedValue(undefined);
    renderHook(() => usePolling(fn, 1000, true));

    await act(async () => {
      await Promise.resolve();
    });
    expect(fn).toHaveBeenCalledTimes(1);

    await act(async () => {
      jest.advanceTimersByTime(1000);
      await Promise.resolve();
    });
    expect(fn).toHaveBeenCalledTimes(2);

    await act(async () => {
      jest.advanceTimersByTime(1000);
      await Promise.resolve();
    });
    expect(fn).toHaveBeenCalledTimes(3);
  });

  it("does not poll when inactive", async () => {
    const fn = jest.fn().mockResolvedValue(undefined);
    renderHook(() => usePolling(fn, 1000, false));

    await act(async () => {
      jest.advanceTimersByTime(5000);
      await Promise.resolve();
    });
    expect(fn).not.toHaveBeenCalled();
  });

  it("stops polling after unmount", async () => {
    const fn = jest.fn().mockResolvedValue(undefined);
    const { unmount } = renderHook(() => usePolling(fn, 1000, true));

    await act(async () => {
      await Promise.resolve();
    });
    expect(fn).toHaveBeenCalledTimes(1);

    unmount();

    await act(async () => {
      jest.advanceTimersByTime(5000);
      await Promise.resolve();
    });
    expect(fn).toHaveBeenCalledTimes(1);
  });
});
