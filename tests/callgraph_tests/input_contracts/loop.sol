contract Loop {
  function f1() public {
    f2();
  }
  function f2() public {
    f3();
  }
  function f3() public {
    f1();
  }
}
