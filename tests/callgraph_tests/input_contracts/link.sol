contract Link {
  function f1() public {
    f2();
  }
  function f2() public {
    f3();
  }
  function f3() public {
    f4();
  }
  function f4() public {
    f5();
  }
  function f5() public {
    f6();
  }
  function f6() public {
  }
}
